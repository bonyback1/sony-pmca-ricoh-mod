#!/usr/bin/env python3
"""
Master Cross-Model Static Verification Testbench Runner
Coordinates all 4 static verification tiers for Sony PlayMemories Camera Apps (PMCA):
- Tier 1: Dalvik API 10 Static Bytecode Verifier (Syntax, Locals/Registers, Opcodes, Catchall, Conflicts)
- Tier 2: PMCA Framework Symbol Auditor (Gen 1 vs Gen 2 Catalogs, Crash Hazards, Fragile HAL, DMA Safety)
- Tier 3: Input Ergonomics Simulator (Dual-Dial, Single-Dial, RX Ring, Touch, 0xe8 Bypass & Key Preservation)
- Tier 4: APK Packaging & Signing Validator (V1 JAR Signatures, SHA-1 Integrity, No V2/V3, No CMS, ZipAlign)

Returns exit code 0 if 100% of executed checks pass; exit code 1 if any check fails; exit code 2 on CLI/config errors.
"""

import sys
import os
import time
import json
import argparse
import datetime
from typing import List, Dict, Optional, Tuple

# Ensure tools/testbench directory is in sys.path
TESTBENCH_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTBENCH_DIR not in sys.path:
    sys.path.insert(0, TESTBENCH_DIR)

from test_dalvik_verification import run_tier1_tests, TierResult as T1Result
from test_pmca_symbols import run_tier2_tests, TierResult as T2Result
from test_input_ergonomics import run_tier3_tests, TierResult as T3Result
from test_apk_signing import run_tier4_tests, TierResult as T4Result


# ---------------------------------------------------------------------------
# ANSI Colors & Formatting
# ---------------------------------------------------------------------------

class ColorFormatter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def green(self, text: str) -> str:
        return f"\033[92m{text}\033[0m" if self.enabled else text

    def red(self, text: str) -> str:
        return f"\033[91m{text}\033[0m" if self.enabled else text

    def yellow(self, text: str) -> str:
        return f"\033[93m{text}\033[0m" if self.enabled else text

    def bold(self, text: str) -> str:
        return f"\033[1m{text}\033[0m" if self.enabled else text

    def cyan(self, text: str) -> str:
        return f"\033[96m{text}\033[0m" if self.enabled else text


# ---------------------------------------------------------------------------
# Master Runner Implementation
# ---------------------------------------------------------------------------

def resolve_targets(apk_arg: Optional[str], smali_arg: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Resolves target APK and Smali directories with sensible defaults."""
    resolved_apk = apk_arg
    resolved_smali = smali_arg

    # If smali not specified, check candidates
    if not resolved_smali:
        smali_candidates = [
            "src/smali",
            "decompiled/PictureEffectPlus/smali",
            "decompiled/Sony_A6000_pictureeffectplus/smali",
            "decompiled/Sony_A6300_pictureeffectplus/smali",
        ]
        for c in smali_candidates:
            if os.path.exists(c):
                resolved_smali = c
                break

    # If APK not specified, check candidates
    if not resolved_apk:
        apk_candidates = [
            "PictureEffectPlus_Ricoh.apk",
            "Ricoh_Camera.apk",
            "PictureEffectPlus_Ricoh_Compat.apk",
            "Ricoh_Official_Mod.apk",
            "official_apks/Sony_A6000_pictureeffectplus.apk",
            "official_apks/Sony_A6300_pictureeffectplus.apk",
        ]
        for c in apk_candidates:
            if os.path.exists(c):
                resolved_apk = c
                break

    return resolved_apk, resolved_smali


def execute_testbench(
    apk_path: Optional[str],
    smali_dir: Optional[str],
    active_tiers: List[int],
    verbose: bool = False,
    colors: Optional[ColorFormatter] = None
) -> Tuple[List[object], bool, float]:
    """
    Executes specified tiers and aggregates results.
    """
    fmt = colors or ColorFormatter(True)
    results = []
    overall_start = time.time()

    # Tier 1: Dalvik Bytecode Verifier
    if 1 in active_tiers:
        if verbose:
            print(fmt.cyan("\n--- [Running Tier 1: Dalvik API 10 Static Bytecode Verifier] ---"))
        t1_res = run_tier1_tests(smali_dir=smali_dir, apk_path=apk_path, verbose=verbose)
        results.append(t1_res)

    # Tier 2: PMCA Symbol Auditor
    if 2 in active_tiers:
        if verbose:
            print(fmt.cyan("\n--- [Running Tier 2: PMCA Framework Symbol Auditor] ---"))
        t2_res = run_tier2_tests(smali_dir=smali_dir, verbose=verbose)
        results.append(t2_res)

    # Tier 3: Input Ergonomics Simulator
    if 3 in active_tiers:
        if verbose:
            print(fmt.cyan("\n--- [Running Tier 3: Input Ergonomics Simulator] ---"))
        t3_res = run_tier3_tests(smali_dir=smali_dir, apk_path=apk_path, verbose=verbose)
        results.append(t3_res)

    # Tier 4: APK Packaging & Signing Validator
    if 4 in active_tiers:
        if verbose:
            print(fmt.cyan("\n--- [Running Tier 4: APK Packaging & Signing Validator] ---"))
        t4_res = run_tier4_tests(apk_path=apk_path, verbose=verbose)
        results.append(t4_res)

    overall_duration = time.time() - overall_start

    # Determine overall pass
    all_passed = True
    for r in results:
        if not r.skipped and not r.passed:
            all_passed = False

    return results, all_passed, overall_duration


def render_ascii_report(
    results: List[object],
    apk_path: Optional[str],
    smali_dir: Optional[str],
    active_tiers: List[int],
    all_passed: bool,
    duration: float,
    colors: ColorFormatter,
    verbose: bool = False
) -> str:
    """Renders the comprehensive ASCII Summary Table and execution metrics."""
    out = []
    w = 84
    sep_double = "=" * w
    sep_single = "-" * w

    out.append(sep_double)
    out.append(colors.bold("                       SONY PMCA TESTBENCH EXECUTION REPORT"))
    out.append(sep_double)
    out.append(f"Target APK   : {apk_path or '[None / Skipped]'}")
    out.append(f"Target Smali : {smali_dir or '[None / Skipped]'}")
    out.append(f"Active Tiers : {', '.join(f'Tier {t}' for t in active_tiers)}")
    timestamp_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    out.append(f"Timestamp    : {timestamp_utc}")
    out.append(sep_single)
    out.append(f"{'Tier':<5} {'Name / Description':<44} {'Checks':<8} {'Passed':<8} {'Failed':<8} {'Status'}")
    out.append(sep_single)

    total_checks = 0
    total_passed = 0
    total_failed = 0

    for r in results:
        t_num = getattr(r, "tier_num", "?")
        t_name = getattr(r, "tier_name", "Unknown Tier")
        skipped = getattr(r, "skipped", False)

        if skipped:
            out.append(f" {t_num:<4} {t_name:<44} {'-':<8} {'-':<8} {'-':<8} {colors.yellow('SKIPPED')}")
            continue

        checks = getattr(r, "checks", [])
        n_checks = len(checks)
        n_passed = sum(1 for c in checks if c.passed)
        n_failed = n_checks - n_passed

        total_checks += n_checks
        total_passed += n_passed
        total_failed += n_failed

        status_str = colors.green("PASS") if r.passed else colors.red("FAIL")
        out.append(f" {t_num:<4} {t_name:<44} {n_checks:<8} {n_passed:<8} {n_failed:<8} {status_str}")

    out.append(sep_single)
    overall_status_str = colors.green("PASS") if all_passed else colors.red("FAIL")
    out.append(
        f"OVERALL RESULT: {colors.bold(overall_status_str)} "
        f"({total_passed}/{total_checks} checks passed in {duration:.3f}s)"
    )
    out.append(sep_double)

    # Detailed breakdown if verbose or any failure
    if verbose or not all_passed:
        out.append("\nDETAILED TIER CHECK BREAKDOWN:")
        for r in results:
            if getattr(r, "skipped", False):
                out.append(f"\n[Tier {r.tier_num}] {r.tier_name}: SKIPPED ({r.skip_reason})")
                continue

            tier_status = colors.green("PASS") if r.passed else colors.red("FAIL")
            out.append(f"\n[Tier {r.tier_num}] {r.tier_name} - {tier_status} ({r.duration:.3f}s)")
            for c in r.checks:
                c_status = colors.green("PASS") if c.passed else colors.red("FAIL")
                out.append(f"  [{c_status}] {c.name} ({c.duration:.3f}s)")
                if c.message:
                    out.append(f"         {c.message}")
                if not c.passed and c.violations:
                    for v in c.violations[:8]:
                        out.append(f"         {colors.red('• ' + v)}")
                    if len(c.violations) > 8:
                        out.append(f"         ... and {len(c.violations) - 8} more violations.")

    return "\n".join(out)


def export_json_report(
    results: List[object],
    apk_path: Optional[str],
    smali_dir: Optional[str],
    active_tiers: List[int],
    all_passed: bool,
    duration: float,
    output_file: str
):
    """Exports testbench execution metrics as a machine-readable JSON file."""
    report_dict = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "overall_passed": all_passed,
        "overall_duration_seconds": duration,
        "target_apk": apk_path,
        "target_smali": smali_dir,
        "active_tiers": active_tiers,
        "tiers": []
    }

    for r in results:
        tier_data = {
            "tier_num": getattr(r, "tier_num", 0),
            "tier_name": getattr(r, "tier_name", ""),
            "passed": getattr(r, "passed", False),
            "skipped": getattr(r, "skipped", False),
            "skip_reason": getattr(r, "skip_reason", ""),
            "duration_seconds": getattr(r, "duration", 0.0),
            "checks": []
        }
        for c in getattr(r, "checks", []):
            tier_data["checks"].append({
                "name": c.name,
                "passed": c.passed,
                "duration_seconds": c.duration,
                "message": c.message,
                "violations": c.violations,
                "warnings": c.warnings
            })
        report_dict["tiers"].append(tier_data)

    os.makedirs(os.path.dirname(os.path.abspath(output_file)) or ".", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Master Automated Cross-Model Static Verification Testbench for Sony PMCA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 tools/testbench/run_testbench.py --help
  python3 tools/testbench/run_testbench.py --tier 1,2,3,4
  python3 tools/testbench/run_testbench.py --tier 1 -v
  python3 tools/testbench/run_testbench.py --apk PictureEffectPlus_Ricoh_Compat.apk
  python3 tools/testbench/run_testbench.py --json-report test_report.json
        """
    )
    parser.add_argument("--apk", "-a", type=str, default=None, help="Path to target APK file")
    parser.add_argument("--smali-dir", "-s", type=str, default=None, help="Path to target Smali directory")
    parser.add_argument("--tier", "-t", type=str, default="all", help="Comma-separated tiers to run: 1,2,3,4 or all (default: all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output showing individual checks and line violations")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI color codes in console output")
    parser.add_argument("--json-report", type=str, default=None, help="Path to output JSON test report")

    # CLI argument parsing with exit code 2 on invalid arguments
    try:
        args = parser.parse_args()
    except SystemExit as e:
        sys.exit(2 if e.code != 0 else 0)

    # Parse active tiers
    tier_str = args.tier.strip().lower()
    if tier_str in ("all", "*"):
        active_tiers = [1, 2, 3, 4]
    else:
        try:
            active_tiers = [int(x.strip()) for x in tier_str.split(",") if x.strip()]
            for t in active_tiers:
                if t not in (1, 2, 3, 4):
                    print(f"Error: Invalid tier number '{t}'. Allowed tiers are 1, 2, 3, 4.", file=sys.stderr)
                    sys.exit(2)
        except ValueError:
            print(f"Error: Invalid tier argument '{args.tier}'. Expected comma-separated numbers (e.g. '1,2,3').", file=sys.stderr)
            sys.exit(2)

    # Validate target file existence if explicitly specified
    if args.apk is not None and not os.path.exists(args.apk):
        print(f"Error: Specified APK file '{args.apk}' does not exist.", file=sys.stderr)
        sys.exit(2)

    if args.smali_dir is not None and not os.path.exists(args.smali_dir):
        print(f"Error: Specified smali directory '{args.smali_dir}' does not exist.", file=sys.stderr)
        sys.exit(2)

    # Resolve target inputs
    resolved_apk, resolved_smali = resolve_targets(args.apk, args.smali_dir)

    colors = ColorFormatter(not args.no_color)

    # Execute testbench tiers
    results, all_passed, duration = execute_testbench(
        apk_path=resolved_apk,
        smali_dir=resolved_smali,
        active_tiers=active_tiers,
        verbose=args.verbose,
        colors=colors
    )

    # Render report
    report_text = render_ascii_report(
        results=results,
        apk_path=resolved_apk,
        smali_dir=resolved_smali,
        active_tiers=active_tiers,
        all_passed=all_passed,
        duration=duration,
        colors=colors,
        verbose=args.verbose
    )
    print(report_text)

    # Export JSON report if requested
    if args.json_report:
        export_json_report(
            results=results,
            apk_path=resolved_apk,
            smali_dir=resolved_smali,
            active_tiers=active_tiers,
            all_passed=all_passed,
            duration=duration,
            output_file=args.json_report
        )
        if args.verbose:
            print(f"\nSaved JSON execution report to {args.json_report}")

    # Exit code: 0 on 100% pass, 1 on any check failure
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
