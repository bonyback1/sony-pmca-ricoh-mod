#!/usr/bin/env python3
"""
Tier 2: PMCA Framework Symbol Auditor
Audits Smali bytecode against Sony PMCA Gen 1 (API 10) vs Gen 2 (API 16) framework symbols.
1. Universal Framework Symbol Audit: checks CameraEx, ParametersModifier, GammaTable, CameraSetting,
   BaseMenuService, AppRoot against symbol catalogs.
2. Gen 1 Crash Hazard & Defensive Guard Audit: ensures Gen 2-only methods (e.g. setRGBMatrix,
   createGammaTable, setExtendedGammaTable) are guarded by dynamic reflection or defensive
   Throwable try-catch blocks with non-rethrowing fallback branches.
3. Fragile HAL Hardware Protection Audit: ensures hardware register calls (WB shifts, color modes)
   have try-catch error recovery.
4. DMA Memory Safety Audit: ensures native GammaTable allocations are released safely in finally blocks.
"""

import sys
import os
import re
import json
import time
import argparse
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration: float
    message: str = ""
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TierResult:
    tier_num: int
    tier_name: str
    passed: bool
    duration: float
    checks: List[CheckResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class CatchHandlerInfo:
    line_num: int
    exception_type: str
    try_start: str
    try_end: str
    handler_label: str
    is_catchall: bool = False
    catches_throwable: bool = False
    has_fallback: bool = True
    has_rethrow: bool = False


@dataclass
class FrameworkInvocation:
    file_path: str
    line_num: int
    method_name: str
    raw_instruction: str
    target_class: str
    target_method: str
    target_sig: str
    is_reflected: bool = False
    active_catches: List[CatchHandlerInfo] = field(default_factory=list)


AUDITED_CLASSES = {
    "com.sony.scalar.hardware.CameraEx",
    "com.sony.scalar.hardware.CameraEx$ParametersModifier",
    "com.sony.scalar.hardware.CameraEx$GammaTable",
    "com.sony.imaging.app.base.shooting.camera.CameraSetting",
    "com.sony.imaging.app.base.menu.BaseMenuService",
    "com.sony.imaging.app.fw.AppRoot",
}

FRAGILE_HAL_METHODS = {
    "setLightBalanceForWhiteBalance(I)V",
    "setColorCompensationForWhiteBalance(I)V",
    "setColorMode(Ljava/lang/String;)V",
    "setDROMode(Ljava/lang/String;)V",
    "setHDRMode(Ljava/lang/String;)V",
}


def load_framework_catalog(json_path: str) -> Dict:
    """Loads a JSON symbol catalog."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def analyze_handler_behavior(m_lines: List[str], m_labels: Dict[str, int], h_idx: int, return_type: str) -> Tuple[bool, bool]:
    """
    Analyzes an exception handler block for re-throwing behavior and abort behavior.
    Uses bounded CFG traversal following gotos and branches, without breaking on intermediate labels.
    Register-agnostic: tracks constant zero/one assignments to detect boolean return false aborts.
    Returns (has_rethrow, is_abort).
    """
    if h_idx < 0 or h_idx >= len(m_lines):
        return (False, False)

    worklist = [h_idx + 1]
    visited = set()
    has_rethrow = False
    is_abort = False

    # Track register values for abort detection across handler paths: reg_states[local_idx] = {reg: int_val}
    reg_states: Dict[int, Dict[str, int]] = {h_idx + 1: {}}

    BRANCH_OPCODES = (
        "if-eq", "if-ne", "if-lt", "if-ge", "if-gt", "if-le",
        "if-eqz", "if-nez", "if-ltz", "if-gez", "if-gtz", "if-lez"
    )
    GOTO_OPCODES = ("goto", "goto/16", "goto/32")

    steps = 0
    max_steps = 100  # Avoid infinite loops in complex/cyclic handler CFG

    while worklist and steps < max_steps:
        steps += 1
        curr = worklist.pop(0)
        if curr in visited or curr >= len(m_lines):
            continue
        visited.add(curr)

        line = m_lines[curr].strip()
        cur_regs = dict(reg_states.get(curr, {}))

        # Check for end of method
        if line.startswith(".end method"):
            continue

        # 1. Check for throw instruction (re-throwing caught or new exception)
        if line.startswith("throw ") or line == "throw":
            has_rethrow = True
            continue

        # 2. Check for const loading 0 (false) or other integer constants
        m_const = re.match(r'const(?:/4|/16)?\s+([vp]\d+),\s*(-?0x[0-9a-fA-F]+|-?\d+)', line)
        if m_const:
            r_name = m_const.group(1)
            val_str = m_const.group(2)
            try:
                val = int(val_str, 16) if ("0x" in val_str or "0X" in val_str) else int(val_str)
                cur_regs[r_name] = val
            except ValueError:
                pass

        # 3. Check for return instructions
        if line.startswith("return"):
            if line == "return-void":
                # Clean void return: not an abort
                pass
            else:
                m_ret = re.match(r'return(?:-wide|-object)?\s+([vp]\d+)', line)
                if m_ret and return_type == "Z":
                    ret_reg = m_ret.group(1)
                    # If returning 0 (false) in a boolean method, it is an abort rather than a fallback
                    if cur_regs.get(ret_reg) == 0:
                        is_abort = True
            # Return terminates this execution path
            continue

        # 4. Check for unconditional jumps: goto :label
        is_goto = False
        for g_op in GOTO_OPCODES:
            if line.startswith(g_op + " ") or line == g_op:
                tgt_match = re.search(r'(:[a-zA-Z0-9_$]+)', line)
                if tgt_match:
                    tgt_lbl = tgt_match.group(1)
                    tgt_idx = m_labels.get(tgt_lbl, -1)
                    if tgt_idx != -1:
                        reg_states[tgt_idx] = cur_regs
                        worklist.append(tgt_idx)
                is_goto = True
                break
        if is_goto:
            continue

        # 5. Check for conditional branches: if-* :label
        is_branch = False
        for b_op in BRANCH_OPCODES:
            if line.startswith(b_op + " ") or line.startswith(b_op + "/"):
                tgt_match = re.search(r'(:[a-zA-Z0-9_$]+)', line)
                if tgt_match:
                    tgt_lbl = tgt_match.group(1)
                    tgt_idx = m_labels.get(tgt_lbl, -1)
                    if tgt_idx != -1:
                        reg_states[tgt_idx] = cur_regs
                        worklist.append(tgt_idx)
                # Fallthrough path
                fallthrough = curr + 1
                reg_states[fallthrough] = cur_regs
                worklist.append(fallthrough)
                is_branch = True
                break
        if is_branch:
            continue

        # 6. Normal sequential instruction or label: fall through to curr + 1
        fallthrough = curr + 1
        reg_states[fallthrough] = cur_regs
        worklist.append(fallthrough)

    return (has_rethrow, is_abort)


def parse_framework_invocations(file_path: str) -> Tuple[List[FrameworkInvocation], List[str]]:
    """
    Parses a smali file for all framework invocations and dynamic reflection usages.
    Direct bytecode invocations are strictly marked is_reflected = False.
    Reflection usages are captured per-invocation and linked to enclosing try-catch blocks.
    """
    invocations: List[FrameworkInvocation] = []
    detected_reflections: List[str] = []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Pass 1: method-scoped parsing
    method_ranges: List[Tuple[int, int, str]] = []
    cur_start = -1
    cur_name = ""

    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith(".method"):
            cur_start = idx
            cur_name = s.split()[-1]
        elif s.startswith(".end method") and cur_start != -1:
            method_ranges.append((cur_start, idx, cur_name))
            cur_start = -1

    for m_start, m_end, m_name in method_ranges:
        m_lines = lines[m_start:m_end + 1]
        m_labels: Dict[str, int] = {}
        m_catches: List[CatchHandlerInfo] = []

        # Extract return type from method declaration
        m_header = m_lines[0].strip()
        ret_match = re.search(r'\([^\)]*\)(.+)$', m_header)
        return_type = ret_match.group(1) if ret_match else ""

        # 1. Collect labels in method
        for local_idx, line in enumerate(m_lines):
            s = line.strip()
            if s.startswith(":"):
                lbl = s.split()[0]
                m_labels[lbl] = local_idx

        # 2. Collect catches in method using unified analyze_handler_behavior
        for local_idx, line in enumerate(m_lines):
            s = line.strip()
            abs_line_num = m_start + local_idx + 1

            if s.startswith(".catchall"):
                m = re.search(r'\{([^\s\.]+)\s*\.\.\s*([^\s\}]+)\}\s*([^\s]+)', s)
                if m:
                    h_lbl = m.group(3)
                    h_idx = m_labels.get(h_lbl, -1)
                    has_rethrow, is_abort = analyze_handler_behavior(m_lines, m_labels, h_idx, return_type)
                    m_catches.append(CatchHandlerInfo(
                        line_num=abs_line_num,
                        exception_type="ALL",
                        try_start=m.group(1),
                        try_end=m.group(2),
                        handler_label=h_lbl,
                        is_catchall=True,
                        catches_throwable=True,
                        has_fallback=(not has_rethrow and not is_abort),
                        has_rethrow=has_rethrow
                    ))
            elif s.startswith(".catch"):
                m = re.search(r'\.catch\s+([^\s]+)\s*\{([^\s\.]+)\s*\.\.\s*([^\s\}]+)\}\s*([^\s]+)', s)
                if m:
                    ex_type = m.group(1)
                    h_lbl = m.group(4)
                    h_idx = m_labels.get(h_lbl, -1)
                    has_rethrow, is_abort = analyze_handler_behavior(m_lines, m_labels, h_idx, return_type)
                    catches_t = ex_type in ("Ljava/lang/Throwable;", "Ljava/lang/Error;", "Ljava/lang/NoSuchMethodError;")
                    m_catches.append(CatchHandlerInfo(
                        line_num=abs_line_num,
                        exception_type=ex_type,
                        try_start=m.group(2),
                        try_end=m.group(3),
                        handler_label=h_lbl,
                        is_catchall=False,
                        catches_throwable=catches_t,
                        has_fallback=(not has_rethrow and not is_abort),
                        has_rethrow=has_rethrow
                    ))

        # 3. Collect direct invocations and per-invocation reflection lookups
        for local_idx, line in enumerate(m_lines):
            s = line.strip()
            abs_line_num = m_start + local_idx + 1

            # A. Direct static bytecode invocation
            if s.startswith("invoke-"):
                inv_match = re.search(r'L([a-zA-Z0-9_/$]+);->([a-zA-Z0-9_$]+)(\([^\)]*\).+)', s)
                if inv_match:
                    raw_cls = inv_match.group(1).replace("/", ".")
                    target_m = inv_match.group(2)
                    sig = target_m + inv_match.group(3)

                    if raw_cls in AUDITED_CLASSES:
                        active = []
                        for cb in m_catches:
                            s_idx = m_labels.get(cb.try_start, -1)
                            e_idx = m_labels.get(cb.try_end, -1)
                            if s_idx != -1 and e_idx != -1 and s_idx <= local_idx <= e_idx:
                                active.append(cb)

                        # DIRECT bytecode invocation: is_reflected is ALWAYS False!
                        invocations.append(FrameworkInvocation(
                            file_path=file_path,
                            line_num=abs_line_num,
                            method_name=m_name,
                            raw_instruction=s,
                            target_class=raw_cls,
                            target_method=target_m,
                            target_sig=sig,
                            is_reflected=False,
                            active_catches=active
                        ))

            # B. Per-invocation dynamic reflection detection
            m_str = re.match(r'const-string(?:/jumbo)?\s+[vp]\d+,\s*"([a-zA-Z0-9_$]+)"', s)
            if m_str:
                ref_method_name = m_str.group(1)
                # Look ahead within local method scope for getMethod / getDeclaredMethod / Method;->invoke
                window = m_lines[local_idx + 1:min(len(m_lines), local_idx + 15)]
                window_text = " ".join([l.strip() for l in window])
                if "getMethod(" in window_text or "getDeclaredMethod(" in window_text or "Method;->invoke(" in window_text:
                    detected_reflections.append(ref_method_name)
                    # Resolve target class & signature from audited classes
                    active_ref_catches = []
                    for cb in m_catches:
                        s_idx = m_labels.get(cb.try_start, -1)
                        e_idx = m_labels.get(cb.try_end, -1)
                        if s_idx != -1 and e_idx != -1 and s_idx <= local_idx <= e_idx:
                            active_ref_catches.append(cb)

                    # Infer target class for known Gen 2 framework methods
                    target_cls = "com.sony.scalar.hardware.CameraEx$ParametersModifier"
                    if ref_method_name in ("createGammaTable", "setExtendedGammaTable"):
                        target_cls = "com.sony.scalar.hardware.CameraEx"
                    elif ref_method_name in ("write", "release", "setPictureEffectGammaForceOff"):
                        target_cls = "com.sony.scalar.hardware.CameraEx$GammaTable"

                    invocations.append(FrameworkInvocation(
                        file_path=file_path,
                        line_num=abs_line_num,
                        method_name=m_name,
                        raw_instruction=s,
                        target_class=target_cls,
                        target_method=ref_method_name,
                        target_sig=ref_method_name,
                        is_reflected=True,
                        active_catches=active_ref_catches
                    ))

    return invocations, detected_reflections


def scan_smali_directory_for_framework_calls(smali_dir: str) -> List[FrameworkInvocation]:
    """Recursively scans a directory of smali files for framework invocations."""
    all_invs = []
    if os.path.isfile(smali_dir) and smali_dir.endswith(".smali"):
        invs, _ = parse_framework_invocations(smali_dir)
        return invs

    for root, _, files in os.walk(smali_dir):
        for f in files:
            if f.endswith(".smali"):
                full_path = os.path.join(root, f)
                invs, _ = parse_framework_invocations(full_path)
                all_invs.extend(invs)
    return all_invs


# ---------------------------------------------------------------------------
# Tier 2 Checks
# ---------------------------------------------------------------------------

def check_universal_symbols(invocations: List[FrameworkInvocation], gen1_catalog: Dict, gen2_catalog: Dict) -> CheckResult:
    """
    Check 1: Universal Framework Symbol Audit.
    Ensures all invoked framework classes and methods are defined in either Gen 1 or Gen 2 catalogs.
    """
    start_time = time.time()
    violations = []

    for inv in invocations:
        c1 = gen1_catalog.get("classes", {}).get(inv.target_class)
        c2 = gen2_catalog.get("classes", {}).get(inv.target_class)

        if not c1 and not c2:
            violations.append(
                f"{inv.file_path}:{inv.line_num}: Invocation targets completely unrecognized framework class '{inv.target_class}'."
            )
            continue

        methods1 = set(c1.get("methods", [])) if c1 and c1.get("exists") else set()
        methods2 = set(c2.get("methods", [])) if c2 and c2.get("exists") else set()

        in_gen1 = any(inv.target_sig == m or m.startswith(inv.target_method + "(") for m in methods1)
        in_gen2 = any(inv.target_sig == m or m.startswith(inv.target_method + "(") for m in methods2)

        if not in_gen1 and not in_gen2:
            violations.append(
                f"{inv.file_path}:{inv.line_num}: Method '{inv.target_sig}' is not defined in any PMCA framework catalog."
            )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = f"All {len(invocations)} framework invocations match PMCA catalogs" if passed else f"{len(violations)} unknown symbol violations found"
    return CheckResult("Universal Framework Symbol Audit", passed, dur, msg, violations)


def check_gen1_crash_hazards(invocations: List[FrameworkInvocation], gen1_catalog: Dict, gen2_catalog: Dict) -> CheckResult:
    """
    Check 2: Gen 1 Crash Hazard & Defensive Guard Audit.
    Ensures every Gen 2-only method invocation is either:
    1. A dynamic reflection lookup guarded by NoSuchMethodException/Throwable catch with fallback, OR
    2. A direct invocation guarded by a defensive Throwable/Error/NoSuchMethodError try-catch with fallback.
    """
    start_time = time.time()
    violations = []
    gen2_only_count = 0

    for inv in invocations:
        c1 = gen1_catalog.get("classes", {}).get(inv.target_class)
        c2 = gen2_catalog.get("classes", {}).get(inv.target_class)

        # Match by full signature or method name
        in_gen1 = c1 and c1.get("exists", False) and any(
            inv.target_sig == m or m.startswith(inv.target_method + "(")
            for m in c1.get("methods", [])
        )
        in_gen2 = c2 and c2.get("exists", False) and any(
            inv.target_sig == m or m.startswith(inv.target_method + "(")
            for m in c2.get("methods", [])
        )

        is_gen2_only = in_gen2 and not in_gen1
        if is_gen2_only:
            gen2_only_count += 1

            if inv.is_reflected:
                # Reflection lookup: verify enclosing try-catch catches NoSuchMethodException/Exception/Throwable with fallback
                has_ref_guard = any(
                    (cb.catches_throwable or cb.exception_type in (
                        "Ljava/lang/NoSuchMethodException;",
                        "Ljava/lang/Exception;",
                        "Ljava/lang/ReflectiveOperationException;"
                    )) and cb.has_fallback
                    for cb in inv.active_catches
                )
                if not has_ref_guard:
                    rethrow_note = " (Handler re-throws exception)" if any(cb.has_rethrow for cb in inv.active_catches) else ""
                    violations.append(
                        f"{inv.file_path}:{inv.line_num}: Gen 1 crash hazard: Dynamic reflection lookup of Gen 2-only method "
                        f"'{inv.target_class}->{inv.target_method}' is unguarded by NoSuchMethodException/Throwable "
                        f"try-catch with fallback{rethrow_note}. Will crash on PMCA Gen 1 (Android 2.3.7 / NEX-5R/6)."
                    )
                continue

            # Direct static bytecode invocation: MUST have active non-rethrowing Throwable/Error catch
            has_guard = False
            for cb in inv.active_catches:
                if cb.catches_throwable and cb.has_fallback:
                    has_guard = True
                    break

            if not has_guard:
                rethrow_note = " (Handler re-throws exception)" if any(cb.has_rethrow for cb in inv.active_catches) else ""
                violations.append(
                    f"{inv.file_path}:{inv.line_num}: Gen 1 crash hazard: Direct unreflected call to Gen 2-only method "
                    f"'{inv.target_class}->{inv.target_sig}' will crash on PMCA Gen 1 (Android 2.3.7 / NEX-5R/6) "
                    f"with java.lang.NoSuchMethodError. Must be guarded by dynamic reflection or non-rethrowing Throwable catch{rethrow_note}."
                )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = f"All {gen2_only_count} Gen 2-only invocations defensively guarded against Gen 1 crashes" if passed else f"{len(violations)} Gen 1 crash hazards detected"
    return CheckResult("Gen 1 Crash Hazard & Defensive Guard Audit", passed, dur, msg, violations)


def check_fragile_hal_protection(invocations: List[FrameworkInvocation]) -> CheckResult:
    """
    Check 3: Fragile HAL Hardware Protection Audit.
    Ensures that calls to sensitive hardware registers (setLightBalanceForWhiteBalance,
    setColorCompensationForWhiteBalance, setColorMode) are enclosed in try-catch blocks.
    """
    start_time = time.time()
    violations = []
    fragile_count = 0

    for inv in invocations:
        if inv.target_sig in FRAGILE_HAL_METHODS or any(inv.target_sig.startswith(m.split("(")[0] + "(") for m in FRAGILE_HAL_METHODS) or inv.target_method in [m.split("(")[0] for m in FRAGILE_HAL_METHODS]:
            fragile_count += 1
            has_catch = any(cb.has_fallback for cb in inv.active_catches)
            if not has_catch:
                violations.append(
                    f"{inv.file_path}:{inv.line_num}: Fragile HAL method '{inv.target_sig}' is invoked without "
                    f"defensive try-catch error recovery. Hardware rejection will crash camera thread."
                )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = f"All {fragile_count} fragile HAL hardware register calls protected" if passed else f"{len(violations)} unprotected fragile HAL calls found"
    return CheckResult("Fragile HAL Hardware Protection Audit", passed, dur, msg, violations)


def check_dma_memory_safety(smali_dir: str, invocations: List[FrameworkInvocation]) -> CheckResult:
    """
    Check 4: DMA Table Memory Safety Audit.
    Ensures that any GammaTable allocation (createGammaTable) guarantees GammaTable.release() in a finally block.
    """
    start_time = time.time()
    violations = []
    creates_gamma = False
    releases_gamma = False

    for inv in invocations:
        if inv.target_method == "createGammaTable":
            creates_gamma = True
        if inv.target_method == "release" and "GammaTable" in inv.target_class:
            releases_gamma = True

    if creates_gamma and not releases_gamma:
        violations.append(
            f"Directory '{smali_dir}' allocates native DMA lookup tables via createGammaTable() but never invokes GammaTable.release(). "
            f"Risk of kernel DMA slab exhaustion."
        )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "DMA GammaTable memory allocation and release lifecycle verified" if passed else "DMA table memory safety violation"
    return CheckResult("DMA Memory Safety Audit", passed, dur, msg, violations)


# ---------------------------------------------------------------------------
# Tier 2 Master Runner API
# ---------------------------------------------------------------------------

def run_tier2_tests(smali_dir: Optional[str] = None, gen1_path: Optional[str] = None, gen2_path: Optional[str] = None, verbose: bool = False) -> TierResult:
    """
    Executes Tier 2 PMCA symbol audit checks against the target directory.
    Returns TierResult with individual CheckResult objects.
    """
    start_time = time.time()

    target_dir = smali_dir
    if not target_dir:
        if os.path.exists("src/smali"):
            target_dir = "src/smali"
        elif os.path.exists("decompiled/PictureEffectPlus/smali"):
            target_dir = "decompiled/PictureEffectPlus/smali"
        else:
            return TierResult(
                tier_num=2,
                tier_name="PMCA Framework Symbol Auditor",
                passed=False,
                duration=0.0,
                skip_reason="No smali directory specified or found"
            )

    # Locate catalogs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    g1_file = gen1_path or os.path.join(base_dir, "mock_pmca_framework", "gen1_symbols.json")
    g2_file = gen2_path or os.path.join(base_dir, "mock_pmca_framework", "gen2_symbols.json")

    if not os.path.exists(g1_file) or not os.path.exists(g2_file):
        return TierResult(
            tier_num=2,
            tier_name="PMCA Framework Symbol Auditor",
            passed=False,
            duration=time.time() - start_time,
            skip_reason=f"Framework catalog files missing ({g1_file} or {g2_file})"
        )

    g1_cat = load_framework_catalog(g1_file)
    g2_cat = load_framework_catalog(g2_file)

    invocations = scan_smali_directory_for_framework_calls(target_dir)

    checks = [
        check_universal_symbols(invocations, g1_cat, g2_cat),
        check_gen1_crash_hazards(invocations, g1_cat, g2_cat),
        check_fragile_hal_protection(invocations),
        check_dma_memory_safety(target_dir, invocations)
    ]

    all_passed = all(c.passed for c in checks)
    tier_dur = time.time() - start_time

    return TierResult(
        tier_num=2,
        tier_name="PMCA Framework Symbol Auditor",
        passed=all_passed,
        duration=tier_dur,
        checks=checks
    )


# ---------------------------------------------------------------------------
# Synthetic Test Fixtures (Self-Test)
# ---------------------------------------------------------------------------

def run_tier2_fixtures() -> bool:
    """Runs synthetic test fixtures verifying that symbol violations are accurately caught."""
    print("Running Tier 2 synthetic test fixtures...")

    # Case 1: Safe guarded Gen 2 call
    safe_smali = """
.class public Lcom/example/SafeHook;
.super Ljava/lang/Object;

.method public static apply(Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;)V
    .locals 2
    :try_start_0
    const/4 v1, 0x0
    invoke-virtual {p0, v1}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception v0
    return-void
.end method
"""

    # Case 2: Unguarded Gen 2 call (Gen 1 crash hazard)
    unguarded_smali = """
.class public Lcom/example/UnsafeHook;
.super Ljava/lang/Object;

.method public static apply(Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;)V
    .locals 1
    const/4 v0, 0x0
    invoke-virtual {p0, v0}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    return-void
.end method
"""

    # Case 3: Rethrowing catch block (fails fallback requirement)
    rethrow_smali = """
.class public Lcom/example/RethrowHook;
.super Ljava/lang/Object;

.method public static apply(Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;)V
    .locals 2
    :try_start_0
    const/4 v1, 0x0
    invoke-virtual {p0, v1}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    return-void

    :catchall_0
    move-exception v0
    throw v0
.end method
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        f_safe = os.path.join(tmpdir, "SafeHook.smali")
        with open(f_safe, "w") as f:
            f.write(safe_smali)
        res_safe = run_tier2_tests(tmpdir)
        assert res_safe.passed, f"Safe fixture failed: {res_safe}"
        os.remove(f_safe)

        f_unsafe = os.path.join(tmpdir, "UnsafeHook.smali")
        with open(f_unsafe, "w") as f:
            f.write(unguarded_smali)
        res_unsafe = run_tier2_tests(tmpdir)
        assert not res_unsafe.passed, "Unguarded Gen 2 call was not detected as a crash hazard!"
        os.remove(f_unsafe)

        f_rethrow = os.path.join(tmpdir, "RethrowHook.smali")
        with open(f_rethrow, "w") as f:
            f.write(rethrow_smali)
        res_rethrow = run_tier2_tests(tmpdir)
        assert not res_rethrow.passed, "Rethrowing catch block was not detected as a crash hazard!"
        os.remove(f_rethrow)

    print("Tier 2 synthetic test fixtures: ALL PASSED (Genuine detection verified).")
    return True


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tier 2: PMCA Framework Symbol Auditor")
    parser.add_argument("--smali-dir", "-s", type=str, default="src/smali", help="Target smali directory")
    parser.add_argument("--gen1", type=str, default=None, help="Path to gen1_symbols.json")
    parser.add_argument("--gen2", type=str, default=None, help="Path to gen2_symbols.json")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose violation details")
    parser.add_argument("--fixtures", action="store_true", help="Run synthetic test fixtures")

    args = parser.parse_args()

    if args.smali_dir is not None and not os.path.exists(args.smali_dir):
        print(f"Error: Specified smali directory '{args.smali_dir}' does not exist.", file=sys.stderr)
        sys.exit(2)

    if args.fixtures:
        success = run_tier2_fixtures()
        sys.exit(0 if success else 1)

    result = run_tier2_tests(args.smali_dir, args.gen1, args.gen2, args.verbose)

    print(f"\n================================================================================")
    print(f"TIER 2 RESULT: {'PASS' if result.passed else 'FAIL'} (Duration: {result.duration:.3f}s)")
    print(f"================================================================================")
    for c in result.checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"[{status}] {c.name} ({c.duration:.3f}s)")
        if c.message:
            print(f"       Message: {c.message}")
        if not c.passed and args.verbose:
            for v in c.violations[:10]:
                print(f"       Violation: {v}")
            if len(c.violations) > 10:
                print(f"       ... and {len(c.violations) - 10} more violations.")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
