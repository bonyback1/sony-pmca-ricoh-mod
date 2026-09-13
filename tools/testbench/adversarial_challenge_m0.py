#!/usr/bin/env python3
"""
Milestone M0 Adversarial Stress Test Suite
Author: challenger_m0_1
Purpose: Empirically stress-test test_dalvik_verification.py and test_pmca_symbols.py
with adversarial edge cases, CFG loop mutations, wide register boundaries, and reflection evasion.
"""

import sys
import os
import tempfile
import traceback

TESTBENCH_DIR = os.path.dirname(os.path.abspath(__file__))
if TESTBENCH_DIR not in sys.path:
    sys.path.insert(0, TESTBENCH_DIR)

from test_dalvik_verification import run_tier1_tests
from test_pmca_symbols import run_tier2_tests


def run_synthetic_test(name: str, smali_code: str, test_tier: int, expected_fail: bool, expected_violation_keyword: str = "") -> dict:
    """
    Executes a synthetic smali test case against Tier 1 or Tier 2.
    Returns test result dict.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "AdversarialTest.smali")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(smali_code)

        if test_tier == 1:
            res = run_tier1_tests(smali_dir=tmpdir)
        else:
            res = run_tier2_tests(smali_dir=tmpdir)

        passed = res.passed
        violations = []
        for c in res.checks:
            if not c.passed:
                violations.extend(c.violations)

        # Bug detected if test should fail (is invalid bytecode or unsafe call) but verifier passed it
        bug_found = False
        if expected_fail and passed:
            bug_found = True
            msg = "FALSE NEGATIVE: Invalid/dangerous code passed verification undetected!"
        elif not expected_fail and not passed:
            bug_found = True
            msg = f"FALSE POSITIVE: Valid code was rejected: {violations}"
        elif expected_fail and not passed and expected_violation_keyword:
            if not any(expected_violation_keyword.lower() in v.lower() for v in violations):
                bug_found = True
                msg = f"WRONG REASON: Failed but missing expected keyword '{expected_violation_keyword}' in {violations}"
            else:
                msg = "Correctly rejected with expected violation."
        else:
            msg = "Expected outcome verified."

        return {
            "name": name,
            "tier": test_tier,
            "expected_fail": expected_fail,
            "actual_passed": passed,
            "bug_found": bug_found,
            "message": msg,
            "violations": violations
        }


def main():
    print("================================================================================")
    print("STARTING EMPIRICAL ADVERSARIAL CHALLENGE FOR MILESTONE M0 (TIERS 1 & 2)")
    print("================================================================================\n")

    test_cases = [
        # ----------------------------------------------------------------------
        # CATEGORY A: WIDE REGISTER PAIRS AT BOUNDARY & PARAM REGISTERS
        # ----------------------------------------------------------------------
        (
            "A1: Wide source register at boundary in move-wide (v1 with .locals 2)",
            """
.class public Lcom/challenge/WideSourceMove;
.super Ljava/lang/Object;

.method public static test()V
    .locals 2
    const-wide/16 v0, 0x0
    # v1 is at boundary (M-1). 64-bit pair requires v1 & v2. v2 is out of bounds!
    move-wide v0, v1
    return-void
.end method
""",
            1,
            True,
            "insufficient"
        ),
        (
            "A2: Wide source register at boundary in cmp-long (v2 with .locals 3)",
            """
.class public Lcom/challenge/WideSourceCmp;
.super Ljava/lang/Object;

.method public static test()V
    .locals 3
    const-wide/16 v1, 0x0
    # v2 is at boundary (M-1). 64-bit pair requires v2 & v3. v3 is out of bounds!
    cmp-long v0, v1, v2
    return-void
.end method
""",
            1,
            True,
            "insufficient"
        ),
        (
            "A3: Wide source register at boundary in add-long (v2 with .locals 3)",
            """
.class public Lcom/challenge/WideSourceAdd;
.super Ljava/lang/Object;

.method public static test()V
    .locals 3
    const-wide/16 v0, 0x0
    const-wide/16 v1, 0x0
    # v2 is at boundary (M-1). 64-bit pair requires v2 & v3. v3 is out of bounds!
    add-long v0, v1, v2
    return-void
.end method
""",
            1,
            True,
            "insufficient"
        ),
        (
            "A4: Out-of-bounds parameter register p99 when using .registers declaration",
            """
.class public Lcom/challenge/ParamRegBounds;
.super Ljava/lang/Object;

.method public static test(I)V
    .registers 2
    # p99 is grossly out of bounds
    const/4 p99, 0x1
    return-void
.end method
""",
            1,
            True,
            "exceeds"
        ),
        (
            "A5: Wide parameter register at boundary (p1 with 2 params requires p2)",
            """
.class public Lcom/challenge/WideParamBoundary;
.super Ljava/lang/Object;

.method public static test(II)V
    .locals 2
    # p0 and p1 exist. move-wide p1 requires p1 & p2. p2 does not exist!
    move-wide v0, p1
    return-void
.end method
""",
            1,
            True,
            "exceeds"
        ),

        # ----------------------------------------------------------------------
        # CATEGORY B: COMPLEX / NESTED TRY-CATCH RANGES & CATCHALL ORDERING
        # ----------------------------------------------------------------------
        (
            "B1: Inverted try-catch range (:try_end before :try_start)",
            """
.class public Lcom/challenge/InvertedTry;
.super Ljava/lang/Object;

.method public static test()V
    .locals 1
    :try_end_0
    nop
    :try_start_0
    nop
    return-void

    .catchall {:try_start_0 .. :try_end_0} :handler

    :handler
    move-exception v0
    return-void
.end method
""",
            1,
            True,
            "try"
        ),

        # ----------------------------------------------------------------------
        # CATEGORY C: CFG LOOPS & REGISTER TYPE MERGE CONFLICTS
        # ----------------------------------------------------------------------
        (
            "C1: CFG loop back-edge type conflict (REF -> PRIM -> back-edge -> read REF)",
            """
.class public Lcom/challenge/LoopConflict;
.super Ljava/lang/Object;

.method public static test(I)V
    .locals 3
    const-string v0, "hello"

    :loop_header
    # First iteration: v0 is String (REF). Subsequent iterations: v0 is int (PRIM32).
    # Dalvik verifier must reject this!
    array-length v1, v0

    const/4 v0, 0x1
    add-int/lit8 p0, p0, -0x1
    if-lez p0, :loop_header

    return-void
.end method
""",
            1,
            True,
            "conflict"
        ),
        (
            "C2: Reading completely uninitialized register (TYPE_UNINIT)",
            """
.class public Lcom/challenge/UninitRead;
.super Ljava/lang/Object;

.method public static test()V
    .locals 2
    # v0 is never initialized before read
    array-length v1, v0
    return-void
.end method
""",
            1,
            True,
            "uninit"
        ),
        (
            "C3: Primitive-expecting instruction (add-int) passed Reference (String)",
            """
.class public Lcom/challenge/RefPassedToPrimitiveOp;
.super Ljava/lang/Object;

.method public static test()V
    .locals 3
    const-string v0, "hello"
    const/4 v1, 0x1
    # add-int expects primitive 32-bit int, not an object reference!
    add-int v2, v0, v1
    return-void
.end method
""",
            1,
            True,
            "primitive"
        ),

        # ----------------------------------------------------------------------
        # CATEGORY D: PMCA SYMBOLS - RE-THROW VS RECOVERY HANDLERS
        # ----------------------------------------------------------------------
        (
            "D1: Re-throwing handler evasion via goto label (throw v0 after label)",
            """
.class public Lcom/challenge/SneakyRethrow;
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
    goto :rethrow_target

    :rethrow_target
    throw v0
.end method
""",
            2,
            True,
            "crash hazard"
        ),
        (
            "D2: .catchall aborting with return false via v1 (asymmetric v0 check)",
            """
.class public Lcom/challenge/CatchallV1Abort;
.super Ljava/lang/Object;

.method public static apply(Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;)Z
    .locals 3
    :try_start_0
    const/4 v1, 0x0
    invoke-virtual {p0, v1}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    :try_end_0
    .catchall {:try_start_0 .. :try_end_0} :catchall_0

    const/4 v2, 0x1
    return v2

    :catchall_0
    move-exception v0
    const/4 v1, 0x0
    return v1
.end method
""",
            2,
            True,
            "crash hazard"
        ),

        # ----------------------------------------------------------------------
        # CATEGORY E: PMCA SYMBOLS - FALSE REFLECTION ATTRIBUTION
        # ----------------------------------------------------------------------
        (
            "E1: False reflection credit on direct call due to distant const-string",
            """
.class public Lcom/challenge/FakeReflection;
.super Ljava/lang/Object;

.method public static dummy()V
    .locals 2
    # Fake reflection snippet somewhere in class
    const-string v0, "setRGBMatrix"
    invoke-virtual {v1, v0}, Ljava/lang/Class;->getMethod(Ljava/lang/String;)Ljava/lang/reflect/Method;
    return-void
.end method

.method public static crashOnGen1(Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;)V
    .locals 1
    const/4 v0, 0x0
    # DIRECT UNREFLECTED CALL that WILL crash on Gen 1!
    invoke-virtual {p0, v0}, Lcom/sony/scalar/hardware/CameraEx$ParametersModifier;->setRGBMatrix([I)V
    return-void
.end method
""",
            2,
            True,
            "crash hazard"
        ),
    ]

    total = len(test_cases)
    bugs_found = 0
    results = []

    for idx, (name, smali, tier, exp_fail, exp_kw) in enumerate(test_cases, 1):
        res = run_synthetic_test(name, smali, tier, exp_fail, exp_kw)
        results.append(res)
        status = "BUG CONFIRMED" if res["bug_found"] else "PASS (HANDLED)"
        if res["bug_found"]:
            bugs_found += 1
            print(f"[{idx}/{total}] [FAILED] {res['name']}")
            print(f"       Outcome: {res['message']}")
            print(f"       Actual Passed: {res['actual_passed']}")
        else:
            print(f"[{idx}/{total}] [PASSED] {res['name']}")
            print(f"       Outcome: {res['message']}")

    print("\n================================================================================")
    print(f"ADVERSARIAL STRESS TEST SUMMARY: {bugs_found}/{total} CRITICAL BUGS EMPIRICALLY REPRODUCED")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
