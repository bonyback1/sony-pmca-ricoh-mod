#!/usr/bin/env python3
"""
Tier 1: Dalvik API 10 Bytecode & Static Smali Verifier
Audits Smali bytecode against Android 2.3.7 (PMCA Gen 1 / API 10) Dalvik VM verification rules:
1. Smali lexical block syntax & label resolution (+ apktool dry-run if applicable).
2. Strict register frame bounds checking (.locals / .registers) with 64-bit wide register pairs.
3. Forbidden modern ART opcodes, constructor invocation rules, Dalvik API 10 interface method bug,
   and return opcode/descriptor consistency.
4. Exception handler canonical ordering (.catchall placement, shadowed handlers, move-exception placement).
5. Register type re-use & dataflow conflict detection via CFG abstract interpretation.
"""

import sys
import os
import re
import time
import argparse
import subprocess
import tempfile
import shutil
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
class SmaliInstruction:
    line_num: int
    raw_line: str
    opcode: str
    registers: List[str]
    operands: str
    is_wide: bool = False


@dataclass
class CatchBlock:
    line_num: int
    exception_type: str
    try_start: str
    try_end: str
    handler: str
    is_catchall: bool = False


@dataclass
class SmaliMethod:
    line_num: int
    class_name: str
    access_flags: List[str]
    name: str
    param_types: List[str]
    return_type: str
    is_static: bool
    locals_count: Optional[int] = None
    registers_count: Optional[int] = None
    param_regs_count: int = 0
    instructions: List[SmaliInstruction] = field(default_factory=list)
    labels: Dict[str, int] = field(default_factory=dict)
    catches: List[CatchBlock] = field(default_factory=list)
    try_ranges: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class SmaliClass:
    file_path: str
    class_name: str
    super_name: str
    source_file: Optional[str] = None
    methods: List[SmaliMethod] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Smali Parser
# ---------------------------------------------------------------------------

WIDE_OPCODES = {
    "const-wide", "const-wide/16", "const-wide/32", "const-wide/high16",
    "move-wide", "move-wide/from16", "move-wide/16", "move-result-wide",
    "return-wide",
    "iget-wide", "iget-wide-volatile", "iput-wide", "iput-wide-volatile",
    "sget-wide", "sget-wide-volatile", "sput-wide", "sput-wide-volatile",
    "aget-wide", "aput-wide",
    "neg-long", "not-long", "neg-double",
    "int-to-long", "int-to-double", "long-to-int", "long-to-float", "long-to-double",
    "float-to-long", "float-to-double", "double-to-int", "double-to-long", "double-to-float",
    "add-long", "sub-long", "mul-long", "div-long", "rem-long", "and-long", "or-long", "xor-long",
    "shl-long", "shr-long", "ushr-long",
    "add-double", "sub-double", "mul-double", "div-double", "rem-double",
    "add-long/2addr", "sub-long/2addr", "mul-long/2addr", "div-long/2addr", "rem-long/2addr",
    "and-long/2addr", "or-long/2addr", "xor-long/2addr", "shl-long/2addr", "shr-long/2addr", "ushr-long/2addr",
    "add-double/2addr", "sub-double/2addr", "mul-double/2addr", "div-double/2addr", "rem-double/2addr",
    "cmpl-double", "cmpg-double", "cmp-long"
}


def is_wide_operand(opcode: str, reg_idx: int) -> bool:
    """
    Returns True if the register at operand index reg_idx in opcode is a 64-bit wide register pair.
    Accurately maps all Dalvik API 10 opcodes across all operand positions (dest and source).
    """
    # 1. Comparisons: operand 0 is 32-bit int destination; operands 1 & 2 are 64-bit source pairs
    if opcode in ("cmpl-double", "cmpg-double", "cmp-long"):
        return reg_idx in (1, 2)

    # 2. Conversions from wide to 32-bit: operand 0 is 32-bit dest; operand 1 is 64-bit wide source
    if opcode in ("long-to-int", "long-to-float", "double-to-int", "double-to-float"):
        return reg_idx == 1

    # 3. Conversions from 32-bit to wide: operand 0 is 64-bit wide dest; operand 1 is 32-bit source
    if opcode in ("int-to-long", "int-to-double", "float-to-long", "float-to-double"):
        return reg_idx == 0

    # 4. Long-to-double and double-to-long: both operand 0 (dest) and operand 1 (source) are wide
    if opcode in ("long-to-double", "double-to-long"):
        return reg_idx in (0, 1)

    # 5. Wide moves: both destination (0) and source (1) are 64-bit pairs
    if opcode in ("move-wide", "move-wide/from16", "move-wide/16"):
        return reg_idx in (0, 1)

    # 6. Shift operations: dest (0) and value (1) are 64-bit; shift distance (2) is 32-bit int
    if opcode in ("shl-long", "shr-long", "ushr-long"):
        return reg_idx in (0, 1)
    if opcode in ("shl-long/2addr", "shr-long/2addr", "ushr-long/2addr"):
        return reg_idx == 0

    # 7. Binary 64-bit arithmetic/bitwise (3 operands): all three operands (0, 1, 2) are wide
    if opcode in (
        "add-long", "sub-long", "mul-long", "div-long", "rem-long", "and-long", "or-long", "xor-long",
        "add-double", "sub-double", "mul-double", "div-double", "rem-double"
    ):
        return reg_idx in (0, 1, 2)

    # 8. Binary 64-bit /2addr operations (2 operands): both operands (0, 1) are wide
    if opcode in (
        "add-long/2addr", "sub-long/2addr", "mul-long/2addr", "div-long/2addr", "rem-long/2addr",
        "and-long/2addr", "or-long/2addr", "xor-long/2addr",
        "add-double/2addr", "sub-double/2addr", "mul-double/2addr", "div-double/2addr", "rem-double/2addr"
    ):
        return reg_idx in (0, 1)

    # 9. Unary 64-bit operations: both dest (0) and source (1) are wide
    if opcode in ("neg-long", "not-long", "neg-double"):
        return reg_idx in (0, 1)

    # 10. All remaining wide opcodes in WIDE_OPCODES have their 64-bit pair at operand 0:
    # (const-wide*, move-result-wide, return-wide, iget-wide*, iput-wide*, sget-wide*, sput-wide*, aget-wide, aput-wide)
    if opcode in WIDE_OPCODES:
        return reg_idx == 0

    return False


FORBIDDEN_ART_OPCODES = {
    "invoke-polymorphic",
    "invoke-polymorphic/range",
    "invoke-custom",
    "invoke-custom/range",
    "const-method-handle",
    "const-method-type",
    "invoke-virtual-quick",
    "invoke-super-quick",
    "iget-quick",
    "iput-quick",
}


def parse_param_descriptors(desc_str: str) -> List[str]:
    """Parses JVM method parameter descriptors into a list of type strings."""
    params = []
    i = 0
    while i < len(desc_str):
        c = desc_str[i]
        if c in "ZBCSIF":
            params.append(c)
            i += 1
        elif c in "JD":
            params.append(c)
            i += 1
        elif c == "L":
            end = desc_str.find(";", i)
            if end == -1:
                break
            params.append(desc_str[i:end + 1])
            i = end + 1
        elif c == "[":
            # Array type
            dim = 1
            while i + dim < len(desc_str) and desc_str[i + dim] == "[":
                dim += 1
            sub_i = i + dim
            if sub_i < len(desc_str):
                if desc_str[sub_i] in "ZBCSIFJD":
                    params.append(desc_str[i:sub_i + 1])
                    i = sub_i + 1
                elif desc_str[sub_i] == "L":
                    end = desc_str.find(";", sub_i)
                    if end == -1:
                        break
                    params.append(desc_str[i:end + 1])
                    i = end + 1
                else:
                    i += 1
            else:
                break
        else:
            i += 1
    return params


def compute_param_registers(param_types: List[str], is_static: bool) -> int:
    """Computes total number of parameter registers required for a method."""
    count = 0 if is_static else 1  # p0 = this for instance methods
    for p in param_types:
        if p in ("J", "D"):
            count += 2
        else:
            count += 1
    return count


def extract_registers(text: str) -> List[str]:
    """Extracts register identifiers (vX or pY) from instruction operands."""
    # Check for range syntax: {vA .. vB} or {pA .. pB}
    range_match = re.search(r'\{([vp]\d+)\s*\.\.\s*([vp]\d+)\}', text)
    if range_match:
        start_reg, end_reg = range_match.group(1), range_match.group(2)
        prefix_s, idx_s = start_reg[0], int(start_reg[1:])
        prefix_e, idx_e = end_reg[0], int(end_reg[1:])
        if prefix_s == prefix_e and idx_s <= idx_e:
            return [f"{prefix_s}{i}" for i in range(idx_s, idx_e + 1)]

    # Standard register matches: {v0, v1, p0} or v0, v1, :label
    regs = re.findall(r'\b([vp]\d+)\b', text)
    return regs


def parse_smali_file(file_path: str) -> Optional[SmaliClass]:
    """Parses a single .smali file into a SmaliClass AST representation."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return None

    class_name = ""
    super_name = ""
    source_file = None
    methods: List[SmaliMethod] = []
    fields: List[str] = []

    current_method: Optional[SmaliMethod] = None
    in_method = False
    in_array_data = False
    in_switch_data = False

    for line_idx, raw_line in enumerate(lines):
        line_num = line_idx + 1
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith(".class"):
            parts = line.split()
            class_name = parts[-1]
        elif line.startswith(".super"):
            parts = line.split()
            super_name = parts[-1]
        elif line.startswith(".source"):
            parts = line.split()
            source_file = parts[-1] if len(parts) > 1 else None
        elif line.startswith(".field"):
            fields.append(line)
        elif line.startswith(".method"):
            in_method = True
            header = line[len(".method"):].strip()
            parts = header.split()
            sig = parts[-1]
            flags = parts[:-1]
            is_static = "static" in flags

            name_match = re.match(r'([^\(]+)\(([^\)]*)\)(.+)', sig)
            if name_match:
                m_name = name_match.group(1)
                param_str = name_match.group(2)
                ret_type = name_match.group(3)
                param_types = parse_param_descriptors(param_str)
            else:
                m_name = sig
                param_types = []
                ret_type = "V"

            param_regs = compute_param_registers(param_types, is_static)
            current_method = SmaliMethod(
                line_num=line_num,
                class_name=class_name,
                access_flags=flags,
                name=m_name,
                param_types=param_types,
                return_type=ret_type,
                is_static=is_static,
                param_regs_count=param_regs
            )
        elif line.startswith(".end method"):
            if current_method:
                methods.append(current_method)
                current_method = None
            in_method = False
            in_array_data = False
            in_switch_data = False
        elif in_method and current_method:
            if line.startswith(".array-data"):
                in_array_data = True
                continue
            elif line.startswith(".end array-data"):
                in_array_data = False
                continue
            elif line.startswith(".packed-switch") or line.startswith(".sparse-switch"):
                in_switch_data = True
                continue
            elif line.startswith(".end packed-switch") or line.startswith(".end sparse-switch"):
                in_switch_data = False
                continue

            if in_array_data or in_switch_data:
                continue

            if line.startswith(".locals"):
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    current_method.locals_count = int(parts[1])
            elif line.startswith(".registers"):
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    current_method.registers_count = int(parts[1])
            elif line.startswith(".catchall"):
                # Format: .catchall {:try_start .. :try_end} :handler
                m = re.search(r'\{([^\s\.]+)\s*\.\.\s*([^\s\}]+)\}\s*([^\s]+)', line)
                if m:
                    current_method.catches.append(CatchBlock(
                        line_num=line_num,
                        exception_type="ALL",
                        try_start=m.group(1),
                        try_end=m.group(2),
                        handler=m.group(3),
                        is_catchall=True
                    ))
            elif line.startswith(".catch"):
                # Format: .catch <Type> {:try_start .. :try_end} :handler
                m = re.search(r'\.catch\s+([^\s]+)\s*\{([^\s\.]+)\s*\.\.\s*([^\s\}]+)\}\s*([^\s]+)', line)
                if m:
                    current_method.catches.append(CatchBlock(
                        line_num=line_num,
                        exception_type=m.group(1),
                        try_start=m.group(2),
                        try_end=m.group(3),
                        handler=m.group(4),
                        is_catchall=False
                    ))
            elif line.startswith(":"):
                # Label definition
                label_name = line.split()[0]
                current_method.labels[label_name] = len(current_method.instructions)
            elif not line.startswith("."):
                # Smali instruction line
                tokens = line.split(maxsplit=1)
                opcode = tokens[0]
                operands = tokens[1] if len(tokens) > 1 else ""
                regs = extract_registers(operands)
                is_wide = opcode in WIDE_OPCODES
                inst = SmaliInstruction(
                    line_num=line_num,
                    raw_line=line,
                    opcode=opcode,
                    registers=regs,
                    operands=operands,
                    is_wide=is_wide
                )
                current_method.instructions.append(inst)

    return SmaliClass(
        file_path=file_path,
        class_name=class_name,
        super_name=super_name,
        source_file=source_file,
        methods=methods,
        fields=fields
    )


def collect_smali_classes(smali_dir: str) -> List[SmaliClass]:
    """Recursively finds and parses all .smali files in the directory."""
    classes = []
    if os.path.isfile(smali_dir) and smali_dir.endswith(".smali"):
        sc = parse_smali_file(smali_dir)
        if sc:
            classes.append(sc)
        return classes

    for root, _, files in os.walk(smali_dir):
        for file in files:
            if file.endswith(".smali"):
                full_path = os.path.join(root, file)
                sc = parse_smali_file(full_path)
                if sc:
                    classes.append(sc)
    return classes


# ---------------------------------------------------------------------------
# Tier 1 Checks
# ---------------------------------------------------------------------------

BRANCH_OPCODES = {
    "goto", "goto/16", "goto/32",
    "if-eq", "if-ne", "if-lt", "if-ge", "if-gt", "if-le",
    "if-eqz", "if-nez", "if-ltz", "if-gez", "if-gtz", "if-lez",
    "packed-switch", "sparse-switch"
}


def check_smali_syntax_and_dryrun(smali_dir: str, classes: List[SmaliClass], apk_path: Optional[str] = None) -> CheckResult:
    """
    Check 1: Smali syntax block balance, branch label existence, and apktool dry-run.
    """
    start_time = time.time()
    violations = []

    # 1. Structural balance and label resolution across all parsed classes
    for sc in classes:
        for m in sc.methods:
            # Check branch targets and label references
            for inst in m.instructions:
                # Catch branches like 'goto :label', 'if-eq v0, v1, :label'
                if inst.opcode in BRANCH_OPCODES:
                    labels_in_operands = re.findall(r'(:[a-zA-Z0-9_\-]+)', inst.operands)
                    for lbl in labels_in_operands:
                        if lbl not in m.labels:
                            violations.append(
                                f"File {sc.file_path}:{inst.line_num}: Branch target label '{lbl}' in method {m.name} is undefined."
                            )

            # Check catch block label definitions and ordering
            for cb in m.catches:
                if cb.try_start not in m.labels:
                    violations.append(
                        f"File {sc.file_path}:{cb.line_num}: try_start label '{cb.try_start}' in method {m.name} is undefined."
                    )
                if cb.try_end not in m.labels:
                    violations.append(
                        f"File {sc.file_path}:{cb.line_num}: try_end label '{cb.try_end}' in method {m.name} is undefined."
                    )
                if cb.handler not in m.labels:
                    violations.append(
                        f"File {sc.file_path}:{cb.line_num}: handler label '{cb.handler}' in method {m.name} is undefined."
                    )
                if cb.try_start in m.labels and cb.try_end in m.labels:
                    start_idx = m.labels[cb.try_start]
                    end_idx = m.labels[cb.try_end]
                    if start_idx >= end_idx:
                        violations.append(
                            f"Method {sc.class_name}->{m.name}:{cb.line_num}: Inverted or empty try range [{cb.try_start} .. {cb.try_end}]: "
                            f"start index {start_idx} >= end index {end_idx}. Dalvik requires start < end."
                        )

    # 2. Optional Apktool dry-run if smali_dir is a decompiled project containing apktool.yml
    apktool_yml = os.path.join(smali_dir, "apktool.yml")
    if os.path.exists(apktool_yml):
        env = os.environ.copy()
        env["PATH"] = f"/opt/homebrew/opt/java/bin:/opt/homebrew/bin:{env.get('PATH', '')}"
        with tempfile.NamedTemporaryFile(suffix=".apk", delete=False) as tmp_apk:
            tmp_apk_path = tmp_apk.name

        try:
            cmd = ["apktool", "b", smali_dir, "-o", tmp_apk_path]
            res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            if res.returncode != 0:
                violations.append(f"apktool dry-run assembly failed: {res.stderr.strip() or res.stdout.strip()}")
        except Exception as e:
            # If apktool not found or fails invocation, record warning only if yml present
            violations.append(f"apktool execution error: {str(e)}")
        finally:
            if os.path.exists(tmp_apk_path):
                os.remove(tmp_apk_path)

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "All smali syntax blocks balanced and labels resolved" if passed else f"{len(violations)} syntax/label violations found"
    return CheckResult("Smali Syntax & Assembler Dry-Run", passed, dur, msg, violations)


def check_register_bounds_and_locals(classes: List[SmaliClass]) -> CheckResult:
    """
    Check 2: Register bounds and .locals/.registers declaration audit.
    Enforces Dalvik API 10 frame bounds including 64-bit wide register pairs.
    """
    start_time = time.time()
    violations = []

    for sc in classes:
        for m in sc.methods:
            # Abstract and native methods have no code body and declare no locals/registers
            if "abstract" in m.access_flags or "native" in m.access_flags:
                continue

            if m.locals_count is None and m.registers_count is None:
                violations.append(
                    f"Method {sc.class_name}->{m.name} at line {m.line_num}: Neither .locals nor .registers declared."
                )
                continue

            max_v_used = -1
            max_p_used = -1

            for inst in m.instructions:
                for reg_idx, reg in enumerate(inst.registers):
                    prefix = reg[0]
                    num = int(reg[1:])
                    is_wide = is_wide_operand(inst.opcode, reg_idx)

                    if prefix == "v":
                        if is_wide:
                            max_v_used = max(max_v_used, num + 1)
                        else:
                            max_v_used = max(max_v_used, num)
                    elif prefix == "p":
                        if is_wide:
                            max_p_used = max(max_p_used, num + 1)
                        else:
                            max_p_used = max(max_p_used, num)

            # Unconditional check on parameter registers across all methods
            if max_p_used >= m.param_regs_count:
                violations.append(
                    f"Method {sc.class_name}->{m.name}:{m.line_num}: Parameter register p{max_p_used} exceeds "
                    f"calculated parameter register count {m.param_regs_count}."
                )

            # Check bounds against .locals
            if m.locals_count is not None:
                allowed_locals = m.locals_count
                if max_v_used >= allowed_locals:
                    violations.append(
                        f"Method {sc.class_name}->{m.name}:{m.line_num}: .locals {allowed_locals} insufficient "
                        f"for register v{max_v_used}. Required .locals >= {max_v_used + 1}."
                    )

            # Check bounds against .registers
            if m.registers_count is not None:
                allowed_registers = m.registers_count
                if allowed_registers < m.param_regs_count:
                    violations.append(
                        f"Method {sc.class_name}->{m.name}:{m.line_num}: .registers {allowed_registers} insufficient "
                        f"for parameter register count {m.param_regs_count}."
                    )
                if max_v_used >= allowed_registers:
                    violations.append(
                        f"Method {sc.class_name}->{m.name}:{m.line_num}: .registers {allowed_registers} insufficient "
                        f"for register v{max_v_used}. Required .registers >= {max_v_used + 1}."
                    )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "All methods strictly within declared register frame bounds" if passed else f"{len(violations)} register bounds violations found"
    return CheckResult("Register Bounds & .locals Audit", passed, dur, msg, violations)


def check_dalvik_api10_opcodes_and_invocations(classes: List[SmaliClass]) -> CheckResult:
    """
    Check 3: Dangerous opcodes, constructor invocation rules, Dalvik API 10 interface method bug,
    and return type consistency.
    """
    start_time = time.time()
    violations = []

    OBJECT_METHODS = {"equals", "hashCode", "toString", "getClass", "wait", "notify", "notifyAll"}

    for sc in classes:
        for m in sc.methods:
            for inst in m.instructions:
                # 1. Forbidden modern ART opcodes
                if inst.opcode in FORBIDDEN_ART_OPCODES:
                    violations.append(
                        f"Method {sc.class_name}->{m.name}:{inst.line_num}: Opcode '{inst.opcode}' is not supported "
                        f"on Dalvik API 10 (Android 2.3.7)."
                    )

                # 2. Constructor <init> invocation rules
                if "<init>" in inst.operands:
                    if inst.opcode.startswith("invoke-") and not inst.opcode.startswith("invoke-direct"):
                        violations.append(
                            f"Method {sc.class_name}->{m.name}:{inst.line_num}: Constructor <init> invoked via '{inst.opcode}'. "
                            f"Dalvik requires invoke-direct or invoke-direct/range."
                        )

                # 3. Explicit <clinit> invocation check
                if "<clinit>" in inst.operands and inst.opcode.startswith("invoke-"):
                    violations.append(
                        f"Method {sc.class_name}->{m.name}:{inst.line_num}: Explicit invocation of <clinit> is forbidden in Dalvik bytecode."
                    )

                # 4. Dalvik API 10 Interface Method Bug: calling java.lang.Object methods via invoke-interface
                if inst.opcode.startswith("invoke-interface"):
                    # Check method name
                    target_match = re.search(r'->([a-zA-Z0-9_$]+)\(', inst.operands)
                    if target_match:
                        target_name = target_match.group(1)
                        if target_name in OBJECT_METHODS:
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: Invoking Object method '{target_name}' via "
                                f"invoke-interface causes IncompatibleClassChangeError on Android 2.3.7. Must use invoke-virtual on Ljava/lang/Object;."
                            )

                # 5. Return opcode vs method return descriptor consistency
                if inst.opcode.startswith("return"):
                    ret_desc = m.return_type
                    if inst.opcode == "return-void":
                        if ret_desc != "V":
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: return-void used in method returning '{ret_desc}'."
                            )
                    elif inst.opcode == "return-object":
                        if not (ret_desc.startswith("L") or ret_desc.startswith("[")):
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: return-object used in method returning non-object '{ret_desc}'."
                            )
                    elif inst.opcode == "return-wide":
                        if ret_desc not in ("J", "D"):
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: return-wide used in method returning non-wide '{ret_desc}'."
                            )
                    elif inst.opcode == "return":
                        if ret_desc not in ("Z", "B", "S", "C", "I", "F"):
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: 32-bit return used in method returning non-32-bit primitive '{ret_desc}'."
                            )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Dalvik API 10 opcodes and virtual invocations conform to VM rules" if passed else f"{len(violations)} opcode/invocation violations found"
    return CheckResult("Dalvik API 10 Opcodes & Virtual Invocation Safety", passed, dur, msg, violations)


def check_catchall_and_exception_handlers(classes: List[SmaliClass]) -> CheckResult:
    """
    Check 4: Catchall ordering and exception handler structure.
    Catches typed handlers appearing after .catchall and checks move-exception placement.
    """
    start_time = time.time()
    violations = []

    for sc in classes:
        for m in sc.methods:
            # Group catches by try range (try_start, try_end)
            range_catches: Dict[Tuple[str, str], List[CatchBlock]] = {}
            for cb in m.catches:
                key = (cb.try_start, cb.try_end)
                range_catches.setdefault(key, []).append(cb)

            # Check try range ordering (start offset must be strictly less than end offset)
            for cb in m.catches:
                if cb.try_start in m.labels and cb.try_end in m.labels:
                    start_idx = m.labels[cb.try_start]
                    end_idx = m.labels[cb.try_end]
                    if start_idx >= end_idx:
                        violations.append(
                            f"Method {sc.class_name}->{m.name}:{cb.line_num}: Inverted or empty try range [{cb.try_start} .. {cb.try_end}]: "
                            f"start index {start_idx} >= end index {end_idx}. Dalvik requires start < end."
                        )

            # Check ordering within each try range
            for (t_start, t_end), cb_list in range_catches.items():
                catchall_seen = False
                catchall_line = -1
                throwable_seen = False

                for cb in cb_list:
                    if catchall_seen:
                        violations.append(
                            f"Method {sc.class_name}->{m.name}:{cb.line_num}: Handler '{cb.exception_type}' for "
                            f"[{t_start} .. {t_end}] appears after .catchall (line {catchall_line}). Handler is unreachable."
                        )

                    if cb.is_catchall:
                        catchall_seen = True
                        catchall_line = cb.line_num

                    if throwable_seen and not cb.is_catchall:
                        violations.append(
                            f"Method {sc.class_name}->{m.name}:{cb.line_num}: Typed handler '{cb.exception_type}' follows "
                            f"Ljava/lang/Throwable;. Handler is shadowed."
                        )

                    if cb.exception_type == "Ljava/lang/Throwable;":
                        throwable_seen = True

            # Verify handler label and move-exception placement
            handler_labels = {cb.handler for cb in m.catches}
            for h_label in handler_labels:
                if h_label in m.labels:
                    inst_idx = m.labels[h_label]
                    if inst_idx < len(m.instructions):
                        first_inst = m.instructions[inst_idx]
                        if first_inst.opcode != "move-exception":
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{first_inst.line_num}: First instruction at exception handler "
                                f"'{h_label}' must be 'move-exception', found '{first_inst.opcode}'."
                            )

            # Ensure move-exception does not appear outside handler entry
            for idx, inst in enumerate(m.instructions):
                if inst.opcode == "move-exception":
                    # Check if instruction index matches any handler label
                    is_at_handler = any(m.labels.get(hl) == idx for hl in handler_labels)
                    if not is_at_handler:
                        violations.append(
                            f"Method {sc.class_name}->{m.name}:{inst.line_num}: 'move-exception' found outside of an exception handler entry."
                        )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Exception handlers and catchall blocks follow canonical Dalvik ordering" if passed else f"{len(violations)} catchall/exception handler violations found"
    return CheckResult("Catchall Ordering & Exception Handlers", passed, dur, msg, violations)


# ---------------------------------------------------------------------------
# Dataflow Abstract Interpretation for Register Type Conflict Detection
# ---------------------------------------------------------------------------

TYPE_UNINIT = 0
TYPE_REF = 1
TYPE_PRIM32 = 2
TYPE_PRIM64_LO = 3
TYPE_PRIM64_HI = 4
TYPE_NULL_CONST = 5
TYPE_CONFLICT = 6

TYPE_NAMES = {
    TYPE_UNINIT: "UNINIT",
    TYPE_REF: "REF",
    TYPE_PRIM32: "PRIM32",
    TYPE_PRIM64_LO: "PRIM64_LO",
    TYPE_PRIM64_HI: "PRIM64_HI",
    TYPE_NULL_CONST: "NULL_CONST",
    TYPE_CONFLICT: "CONFLICT",
}


def merge_reg_types(t1: int, t2: int) -> int:
    """Lattice join function for Dalvik register types."""
    if t1 == t2:
        return t1
    if t1 == TYPE_UNINIT:
        return t2
    if t2 == TYPE_UNINIT:
        return t1
    if t1 == TYPE_NULL_CONST:
        return t2
    if t2 == TYPE_NULL_CONST:
        return t1
    return TYPE_CONFLICT


def check_register_type_conflicts(classes: List[SmaliClass]) -> CheckResult:
    """
    Check 5: Register type re-use and dataflow conflict detection via CFG fixpoint abstract interpretation.
    Analyzes all control flow paths (including loop backedges and exception handlers) to ensure:
    1. No register merges incompatible types (REF vs PRIM) and is subsequently read without redefinition.
    2. No instruction reads an uninitialized register (TYPE_UNINIT).
    3. No instruction expecting a reference receives a primitive.
    4. No instruction expecting a primitive receives an object reference.
    """
    from collections import deque
    start_time = time.time()
    violations = []

    PRIM_EXPECTING_OPCODES = {
        "add-int", "sub-int", "mul-int", "div-int", "rem-int", "and-int", "or-int", "xor-int", "shl-int", "shr-int", "ushr-int",
        "add-int/2addr", "sub-int/2addr", "mul-int/2addr", "div-int/2addr", "rem-int/2addr", "and-int/2addr", "or-int/2addr", "xor-int/2addr", "shl-int/2addr", "shr-int/2addr", "ushr-int/2addr",
        "add-int/lit8", "sub-int/lit8", "mul-int/lit8", "div-int/lit8", "rem-int/lit8", "and-int/lit8", "or-int/lit8", "xor-int/lit8", "shl-int/lit8", "shr-int/lit8", "ushr-int/lit8",
        "add-int/lit16", "sub-int/lit16", "mul-int/lit16", "div-int/lit16", "rem-int/lit16", "and-int/lit16", "or-int/lit16", "xor-int/lit16",
        "add-long", "sub-long", "mul-long", "div-long", "rem-long", "and-long", "or-long", "xor-long", "shl-long", "shr-long", "ushr-long",
        "add-long/2addr", "sub-long/2addr", "mul-long/2addr", "div-long/2addr", "rem-long/2addr", "and-long/2addr", "or-long/2addr", "xor-long/2addr", "shl-long/2addr", "shr-long/2addr", "ushr-long/2addr",
        "add-float", "sub-float", "mul-float", "div-float", "rem-float",
        "add-float/2addr", "sub-float/2addr", "mul-float/2addr", "div-float/2addr", "rem-float/2addr",
        "add-double", "sub-double", "mul-double", "div-double", "rem-double",
        "add-double/2addr", "sub-double/2addr", "mul-double/2addr", "div-double/2addr", "rem-double/2addr",
        "neg-int", "not-int", "neg-long", "not-long", "neg-float", "neg-double",
        "int-to-long", "int-to-float", "int-to-double", "long-to-int", "long-to-float", "long-to-double",
        "float-to-int", "float-to-long", "float-to-double", "double-to-int", "double-to-long", "double-to-float",
        "int-to-byte", "int-to-char", "int-to-short",
        "cmpl-float", "cmpg-float", "cmpl-double", "cmpg-double", "cmp-long",
        "if-lt", "if-ge", "if-gt", "if-le", "if-ltz", "if-gez", "if-gtz", "if-lez",
        "return"
    }

    def merge_reg_states(s1: Dict[int, int], s2: Dict[int, int], total_regs: int) -> Dict[int, int]:
        """Component-wise lattice join of register typing states."""
        merged = {}
        for r in range(total_regs):
            t1 = s1.get(r, TYPE_UNINIT)
            t2 = s2.get(r, TYPE_UNINIT)
            if t1 == t2:
                merged[r] = t1
            elif t1 == TYPE_NULL_CONST and t2 in (TYPE_REF, TYPE_PRIM32):
                merged[r] = t2
            elif t2 == TYPE_NULL_CONST and t1 in (TYPE_REF, TYPE_PRIM32):
                merged[r] = t1
            else:
                merged[r] = TYPE_CONFLICT
        return merged

    for sc in classes:
        for m in sc.methods:
            if "abstract" in m.access_flags or "native" in m.access_flags or not m.instructions:
                continue

            num_params = m.param_regs_count
            if m.locals_count is not None:
                num_locals = m.locals_count
                total_regs = num_locals + num_params
            elif m.registers_count is not None:
                total_regs = m.registers_count
                num_locals = max(0, total_regs - num_params)
            else:
                num_locals = 16
                total_regs = num_locals + num_params

            def reg_to_idx(r: str) -> Optional[int]:
                if r.startswith("v"):
                    idx = int(r[1:])
                    return idx if idx < total_regs else None
                elif r.startswith("p"):
                    idx = int(r[1:])
                    return (num_locals + idx) if idx < num_params else None
                return None

            entry_state: Dict[int, int] = {i: TYPE_UNINIT for i in range(total_regs)}
            if not m.is_static and num_locals < total_regs:
                entry_state[num_locals] = TYPE_REF

            cur_p = 1 if not m.is_static else 0
            for pt in m.param_types:
                p_idx = num_locals + cur_p
                if p_idx < total_regs:
                    if pt.startswith("L") or pt.startswith("["):
                        entry_state[p_idx] = TYPE_REF
                        cur_p += 1
                    elif pt in ("J", "D"):
                        entry_state[p_idx] = TYPE_PRIM64_LO
                        if p_idx + 1 < total_regs:
                            entry_state[p_idx + 1] = TYPE_PRIM64_HI
                        cur_p += 2
                    else:
                        entry_state[p_idx] = TYPE_PRIM32
                        cur_p += 1

            # Instruction incoming typing states: None indicates unreached block (lattice bottom)
            in_states: List[Optional[Dict[int, int]]] = [None] * len(m.instructions)
            in_states[0] = entry_state.copy()

            # Pre-compute try block coverage for each instruction index
            inst_catches: List[List[CatchBlock]] = [[] for _ in range(len(m.instructions))]
            for cb in m.catches:
                if cb.try_start in m.labels and cb.try_end in m.labels and cb.handler in m.labels:
                    s_idx = m.labels[cb.try_start]
                    e_idx = m.labels[cb.try_end]
                    if s_idx < e_idx:
                        for i in range(s_idx, min(e_idx, len(m.instructions))):
                            inst_catches[i].append(cb)

            worklist = deque([0])
            in_worklist = {0}
            max_iter = 20000 + 100 * len(m.instructions)
            iter_count = 0

            def parse_inst_transfer(inst: SmaliInstruction, cur_state: Dict[int, int]) -> Tuple[Optional[str], Optional[int]]:
                dest_reg = None
                dest_type = None
                op = inst.opcode
                regs = inst.registers
                if op.startswith("invoke-"):
                    pass
                elif op.startswith("sput") or op.startswith("iput") or op.startswith("aput"):
                    pass
                elif op in ("fill-array-data", "monitor-enter", "monitor-exit", "nop"):
                    pass
                elif op.startswith("packed-switch") or op.startswith("sparse-switch"):
                    pass
                elif op.startswith("return") or op.startswith("if-") or op.startswith("goto") or op == "throw":
                    pass
                elif op == "move-result-object":
                    if regs: dest_reg = regs[0]; dest_type = TYPE_REF
                elif op == "move-result-wide":
                    if regs: dest_reg = regs[0]; dest_type = TYPE_PRIM64_LO
                elif op.startswith("move-result"):
                    if regs: dest_reg = regs[0]; dest_type = TYPE_PRIM32
                elif op == "move-exception":
                    if regs: dest_reg = regs[0]; dest_type = TYPE_REF
                elif op.startswith("move-object"):
                    if len(regs) >= 2:
                        dest_reg = regs[0]
                        s_idx = reg_to_idx(regs[1])
                        dest_type = cur_state.get(s_idx, TYPE_REF) if s_idx is not None else TYPE_REF
                elif op.startswith("move-wide"):
                    if len(regs) >= 2: dest_reg = regs[0]; dest_type = TYPE_PRIM64_LO
                elif op.startswith("move"):
                    if len(regs) >= 2:
                        dest_reg = regs[0]
                        s_idx = reg_to_idx(regs[1])
                        dest_type = cur_state.get(s_idx, TYPE_PRIM32) if s_idx is not None else TYPE_PRIM32
                elif op.startswith("const-string") or op == "const-class":
                    if regs: dest_reg = regs[0]; dest_type = TYPE_REF
                elif op == "const/4" and re.search(r'(?:^|[,\s])0x0(?:\s*#.*)?$', inst.operands.strip()):
                    if regs: dest_reg = regs[0]; dest_type = TYPE_NULL_CONST
                elif op.startswith("const-wide"):
                    if regs: dest_reg = regs[0]; dest_type = TYPE_PRIM64_LO
                elif op.startswith("const"):
                    if regs: dest_reg = regs[0]; dest_type = TYPE_PRIM32
                elif op in ("new-instance", "new-array"):
                    if regs: dest_reg = regs[0]; dest_type = TYPE_REF
                elif op in ("array-length", "instance-of"):
                    if regs: dest_reg = regs[0]; dest_type = TYPE_PRIM32
                elif op == "check-cast":
                    if regs: dest_reg = regs[0]; dest_type = TYPE_REF
                elif op.startswith("sget"):
                    if regs:
                        dest_reg = regs[0]
                        dest_type = TYPE_REF if "object" in op else (TYPE_PRIM64_LO if "wide" in op else TYPE_PRIM32)
                elif op.startswith("iget"):
                    if regs:
                        dest_reg = regs[0]
                        dest_type = TYPE_REF if "object" in op else (TYPE_PRIM64_LO if "wide" in op else TYPE_PRIM32)
                elif op.startswith("aget"):
                    if regs:
                        dest_reg = regs[0]
                        dest_type = TYPE_REF if "object" in op else (TYPE_PRIM64_LO if "wide" in op else TYPE_PRIM32)
                elif "/2addr" in op:
                    if regs:
                        dest_reg = regs[0]
                        dest_type = TYPE_PRIM64_LO if ("-long" in op or "-double" in op) else TYPE_PRIM32
                elif any(op.startswith(p) for p in ("add-", "sub-", "mul-", "div-", "rem-", "and-", "or-", "xor-", "shl-", "shr-", "ushr-", "cmp")):
                    if regs:
                        dest_reg = regs[0]
                        dest_type = TYPE_PRIM64_LO if ("-long" in op or "-double" in op) else TYPE_PRIM32
                elif any(op.startswith(p) for p in ("neg-", "not-", "int-to-", "float-to-", "long-to-", "double-to-")):
                    if regs:
                        dest_reg = regs[0]
                        dest_type = TYPE_PRIM64_LO if (op.endswith("-long") or op.endswith("-double")) else TYPE_PRIM32
                elif regs:
                    dest_reg = regs[0]
                    dest_type = TYPE_PRIM32
                return dest_reg, dest_type

            # Worklist CFG fixpoint iteration loop
            while worklist and iter_count < max_iter:
                iter_count += 1
                idx = worklist.popleft()
                in_worklist.discard(idx)

                cur_in = in_states[idx]
                if cur_in is None:
                    continue

                # 1. Propagate pre-instruction state to enclosing catch handlers
                for cb in inst_catches[idx]:
                    if cb.handler in m.labels:
                        h_idx = m.labels[cb.handler]
                        if h_idx < len(m.instructions):
                            prev_h = in_states[h_idx]
                            if prev_h is None:
                                in_states[h_idx] = cur_in.copy()
                                if h_idx not in in_worklist:
                                    worklist.append(h_idx)
                                    in_worklist.add(h_idx)
                            else:
                                merged_h = merge_reg_states(prev_h, cur_in, total_regs)
                                if merged_h != prev_h:
                                    in_states[h_idx] = merged_h
                                    if h_idx not in in_worklist:
                                        worklist.append(h_idx)
                                        in_worklist.add(h_idx)

                inst = m.instructions[idx]
                op = inst.opcode
                regs = inst.registers
                dest_reg, dest_type = parse_inst_transfer(inst, cur_in)

                next_state = cur_in.copy()
                if dest_reg and dest_type is not None:
                    d_idx = reg_to_idx(dest_reg)
                    if d_idx is not None:
                        next_state[d_idx] = dest_type
                        if dest_type == TYPE_PRIM64_LO and d_idx + 1 < total_regs:
                            next_state[d_idx + 1] = TYPE_PRIM64_HI

                successors = []
                is_uncond = op in ("goto", "goto/16", "goto/32") or op.startswith("return") or op == "throw"
                if not is_uncond and idx + 1 < len(m.instructions):
                    successors.append(idx + 1)

                if op in BRANCH_OPCODES:
                    labels_in_operands = re.findall(r"(:[a-zA-Z0-9_\-]+)", inst.operands)
                    for lbl in labels_in_operands:
                        if lbl in m.labels:
                            tgt_idx = m.labels[lbl]
                            if tgt_idx < len(m.instructions):
                                successors.append(tgt_idx)

                for succ in successors:
                    prev_s = in_states[succ]
                    if prev_s is None:
                        in_states[succ] = next_state.copy()
                        if succ not in in_worklist:
                            worklist.append(succ)
                            in_worklist.add(succ)
                    else:
                        merged_s = merge_reg_states(prev_s, next_state, total_regs)
                        if merged_s != prev_s:
                            in_states[succ] = merged_s
                            if succ not in in_worklist:
                                worklist.append(succ)
                                in_worklist.add(succ)

            # Verification pass over all reachable instructions at converged fixpoint
            for idx, inst in enumerate(m.instructions):
                cur_state = in_states[idx]
                if cur_state is None:
                    continue

                op = inst.opcode
                regs = inst.registers
                read_regs = []
                ref_expected_regs = []
                prim_expected_regs = []

                if op.startswith("invoke-"):
                    read_regs = list(regs)
                    if not op.startswith("invoke-static") and regs:
                        ref_expected_regs.append(regs[0])
                elif op in ("move-result-object", "move-result-wide", "move-exception") or op.startswith("move-result"):
                    pass
                elif op.startswith("move-object"):
                    if len(regs) >= 2:
                        read_regs = [regs[1]]
                        ref_expected_regs = [regs[1]]
                elif op.startswith("move-wide") or op.startswith("move"):
                    if len(regs) >= 2:
                        read_regs = [regs[1]]
                elif op == "new-array":
                    if len(regs) >= 2:
                        read_regs = [regs[1]]
                        prim_expected_regs = [regs[1]]
                elif op in ("array-length", "instance-of"):
                    if len(regs) >= 2:
                        read_regs = [regs[1]]
                        ref_expected_regs = [regs[1]]
                elif op == "fill-array-data":
                    if regs:
                        read_regs = [regs[0]]
                        ref_expected_regs = [regs[0]]
                elif op in ("monitor-enter", "monitor-exit"):
                    if regs:
                        read_regs = [regs[0]]
                        ref_expected_regs = [regs[0]]
                elif op == "check-cast":
                    if regs:
                        read_regs = [regs[0]]
                        ref_expected_regs = [regs[0]]
                elif op.startswith("sput"):
                    if regs:
                        read_regs = [regs[0]]
                        if op == "sput-object":
                            ref_expected_regs.append(regs[0])
                        elif not op.startswith("sput-wide"):
                            prim_expected_regs.append(regs[0])
                elif op.startswith("iget"):
                    if len(regs) >= 2:
                        read_regs = [regs[1]]
                        ref_expected_regs = [regs[1]]
                elif op.startswith("iput"):
                    if len(regs) >= 2:
                        read_regs = [regs[0], regs[1]]
                        ref_expected_regs = [regs[1]]
                        if op == "iput-object":
                            ref_expected_regs.append(regs[0])
                        elif not op.startswith("iput-wide"):
                            prim_expected_regs.append(regs[0])
                elif op.startswith("aget"):
                    if len(regs) >= 3:
                        read_regs = [regs[1], regs[2]]
                        ref_expected_regs = [regs[1]]
                        prim_expected_regs = [regs[2]]
                elif op.startswith("aput"):
                    if len(regs) >= 3:
                        read_regs = [regs[0], regs[1], regs[2]]
                        ref_expected_regs = [regs[1]]
                        prim_expected_regs = [regs[2]]
                        if op == "aput-object":
                            ref_expected_regs.append(regs[0])
                        else:
                            prim_expected_regs.append(regs[0])
                elif op.startswith("return"):
                    read_regs = list(regs)
                    if op == "return-object" and regs:
                        ref_expected_regs.append(regs[0])
                    elif op == "return" and regs:
                        prim_expected_regs.append(regs[0])
                elif op.startswith("if-"):
                    read_regs = list(regs)
                    if op in ("if-lt", "if-ge", "if-gt", "if-le", "if-ltz", "if-gez", "if-gtz", "if-lez"):
                        prim_expected_regs.extend(regs)
                elif "/2addr" in op:
                    if len(regs) >= 2:
                        read_regs = [regs[0], regs[1]]
                        if op in PRIM_EXPECTING_OPCODES:
                            prim_expected_regs.extend([regs[0], regs[1]])
                elif any(op.startswith(p) for p in ("add-", "sub-", "mul-", "div-", "rem-", "and-", "or-", "xor-", "shl-", "shr-", "ushr-", "cmp")):
                    if len(regs) >= 3:
                        read_regs = [regs[1], regs[2]]
                    elif len(regs) >= 2:
                        read_regs = [regs[1]]
                    if op in PRIM_EXPECTING_OPCODES:
                        prim_expected_regs.extend(read_regs)
                elif any(op.startswith(p) for p in ("neg-", "not-", "int-to-", "float-to-", "long-to-", "double-to-")):
                    if len(regs) >= 2:
                        read_regs = [regs[1]]
                        prim_expected_regs = [regs[1]]
                elif op == "throw":
                    if regs:
                        read_regs = [regs[0]]
                        ref_expected_regs = [regs[0]]
                elif not op.startswith("const") and not op == "new-instance":
                    if len(regs) > 1:
                        read_regs = regs[1:]

                # 1. Check CONFLICT reads
                for r in read_regs:
                    r_idx = reg_to_idx(r)
                    if r_idx is not None:
                        t = cur_state.get(r_idx, TYPE_UNINIT)
                        if t == TYPE_CONFLICT:
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: Instruction reads register {r} "
                                f"which has CONFLICT type (merged Reference vs Primitive across branches). "
                                f"Dalvik API 10 verifier rejects reading conflicting registers."
                            )

                # 2. Check UNINIT reads
                for r in read_regs:
                    r_idx = reg_to_idx(r)
                    if r_idx is not None:
                        t = cur_state.get(r_idx, TYPE_UNINIT)
                        if t == TYPE_UNINIT:
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: Instruction '{op}' reads uninitialized register {r}. "
                                f"Dalvik API 10 verifier rejects reading uninitialized registers."
                            )

                # 3. Check reference-expected registers
                for r in ref_expected_regs:
                    r_idx = reg_to_idx(r)
                    if r_idx is not None:
                        t = cur_state.get(r_idx, TYPE_UNINIT)
                        if t in (TYPE_PRIM32, TYPE_PRIM64_LO, TYPE_PRIM64_HI):
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: Instruction '{op}' expects object reference "
                                f"in {r}, but register holds primitive type ({TYPE_NAMES[t]})."
                            )

                # 4. Check primitive-expected registers
                for r in prim_expected_regs:
                    r_idx = reg_to_idx(r)
                    if r_idx is not None:
                        t = cur_state.get(r_idx, TYPE_UNINIT)
                        if t == TYPE_REF:
                            violations.append(
                                f"Method {sc.class_name}->{m.name}:{inst.line_num}: Instruction '{op}' expects primitive type "
                                f"in {r}, but register holds object reference (REF). Dalvik verifier rejects passing references to primitive operations."
                            )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "No register type merge conflicts detected on control flow paths" if passed else f"{len(violations)} register type conflict violations found"
    return CheckResult("Register Type Conflict Detection", passed, dur, msg, violations)


# ---------------------------------------------------------------------------
# Tier 1 Master Runner API
# ---------------------------------------------------------------------------

def run_tier1_tests(smali_dir: Optional[str] = None, apk_path: Optional[str] = None, verbose: bool = False) -> TierResult:
    """
    Executes Tier 1 Dalvik verification checks against the target directory.
    Returns TierResult with individual CheckResult objects.
    """
    start_time = time.time()

    target_dir = smali_dir
    if not target_dir:
        # Default auto-discovery
        if os.path.exists("src/smali"):
            target_dir = "src/smali"
        elif os.path.exists("decompiled/PictureEffectPlus"):
            target_dir = "decompiled/PictureEffectPlus"
        else:
            return TierResult(
                tier_num=1,
                tier_name="Dalvik API 10 Static Bytecode Verifier",
                passed=False,
                duration=0.0,
                skip_reason="No smali directory specified or found"
            )

    classes = collect_smali_classes(target_dir)
    if not classes:
        return TierResult(
            tier_num=1,
            tier_name="Dalvik API 10 Static Bytecode Verifier",
            passed=False,
            duration=time.time() - start_time,
            skip_reason=f"No smali classes found in {target_dir}"
        )

    checks = [
        check_smali_syntax_and_dryrun(target_dir, classes, apk_path),
        check_register_bounds_and_locals(classes),
        check_dalvik_api10_opcodes_and_invocations(classes),
        check_catchall_and_exception_handlers(classes),
        check_register_type_conflicts(classes)
    ]

    all_passed = all(c.passed for c in checks)
    tier_dur = time.time() - start_time

    return TierResult(
        tier_num=1,
        tier_name="Dalvik API 10 Static Bytecode Verifier",
        passed=all_passed,
        duration=tier_dur,
        checks=checks
    )


# ---------------------------------------------------------------------------
# Synthetic Test Fixtures (Self-Test)
# ---------------------------------------------------------------------------

def run_tier1_fixtures() -> bool:
    """Runs synthetic test fixtures verifying that violations are accurately caught."""
    print("Running Tier 1 synthetic test fixtures...")

    # Case 1: Valid smali
    valid_smali = """
.class public Lcom/example/Valid;
.super Ljava/lang/Object;

.method public constructor <init>()V
    .registers 1
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public static testValid(I)I
    .locals 2
    const/4 v0, 0x1
    add-int/2addr v0, p0
    return v0
.end method
"""

    # Case 2: Out of bounds register (.locals 1 using v2)
    invalid_reg_smali = """
.class public Lcom/example/InvalidReg;
.super Ljava/lang/Object;

.method public static testReg()V
    .locals 1
    const/4 v2, 0x5
    return-void
.end method
"""

    # Case 3: Forbidden ART opcode (invoke-polymorphic)
    invalid_opcode_smali = """
.class public Lcom/example/InvalidOpcode;
.super Ljava/lang/Object;

.method public static testArt()V
    .locals 1
    invoke-polymorphic {v0}, Ljava/lang/invoke/MethodHandle;->invoke([Ljava/lang/Object;)Ljava/lang/Object;
    return-void
.end method
"""

    # Case 4: Misplaced catchall before typed catch
    invalid_catchall_smali = """
.class public Lcom/example/InvalidCatchall;
.super Ljava/lang/Object;

.method public static testCatch()V
    .locals 1
    :try_start_0
    const/4 v0, 0x1
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    :catchall_0
    move-exception v0
    return-void

    :catch_0
    move-exception v0
    return-void
.end method
"""

    # Case 5: Register merge conflict (const-string vs const/4 non-zero merged and read)
    invalid_conflict_smali = """
.class public Lcom/example/InvalidConflict;
.super Ljava/lang/Object;

.method public static testConflict(Z)V
    .locals 2
    if-eqz p0, :cond_ref
    const/4 v0, 0x1
    goto :join

    :cond_ref
    const-string v0, "string"

    :join
    array-length v1, v0
    return-void
.end method
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write valid file
        f_valid = os.path.join(tmpdir, "Valid.smali")
        with open(f_valid, "w") as f:
            f.write(valid_smali)
        res_valid = run_tier1_tests(tmpdir)
        assert res_valid.passed, f"Valid fixture failed: {res_valid}"

        # Write invalid reg file
        f_reg = os.path.join(tmpdir, "InvalidReg.smali")
        with open(f_reg, "w") as f:
            f.write(invalid_reg_smali)
        res_reg = run_tier1_tests(tmpdir)
        assert not res_reg.passed, "Register bounds check failed to detect violation!"
        os.remove(f_reg)

        # Write invalid opcode file
        f_op = os.path.join(tmpdir, "InvalidOpcode.smali")
        with open(f_op, "w") as f:
            f.write(invalid_opcode_smali)
        res_op = run_tier1_tests(tmpdir)
        assert not res_op.passed, "Forbidden opcode check failed to detect violation!"
        os.remove(f_op)

        # Write invalid catchall file
        f_ca = os.path.join(tmpdir, "InvalidCatchall.smali")
        with open(f_ca, "w") as f:
            f.write(invalid_catchall_smali)
        res_ca = run_tier1_tests(tmpdir)
        assert not res_ca.passed, "Catchall ordering check failed to detect violation!"
        os.remove(f_ca)

        # Write invalid conflict file
        f_cf = os.path.join(tmpdir, "InvalidConflict.smali")
        with open(f_cf, "w") as f:
            f.write(invalid_conflict_smali)
        res_cf = run_tier1_tests(tmpdir)
        assert not res_cf.passed, "Conflict check failed to detect violation!"
        os.remove(f_cf)

    print("Tier 1 synthetic test fixtures: ALL PASSED (Genuine detection verified).")
    return True


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tier 1: Dalvik API 10 Static Bytecode Verifier")
    parser.add_argument("--smali-dir", "-s", type=str, default="src/smali", help="Target smali directory")
    parser.add_argument("--apk", "-a", type=str, default=None, help="Target APK file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose violation details")
    parser.add_argument("--fixtures", action="store_true", help="Run synthetic test fixtures")

    args = parser.parse_args()

    if args.smali_dir is not None and not os.path.exists(args.smali_dir):
        print(f"Error: Specified smali directory '{args.smali_dir}' does not exist.", file=sys.stderr)
        sys.exit(2)

    if args.fixtures:
        success = run_tier1_fixtures()
        sys.exit(0 if success else 1)

    result = run_tier1_tests(args.smali_dir, args.apk, args.verbose)

    print(f"\n================================================================================")
    print(f"TIER 1 RESULT: {'PASS' if result.passed else 'FAIL'} (Duration: {result.duration:.3f}s)")
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
