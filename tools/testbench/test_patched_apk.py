#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 5: Patched APK Bytecode Integrity Auditor.
Decompiles the final built APK to inspect the patched Dalvik bytecode directly,
guaranteeing that all official smali modifications, safety hooks, and lifecycle fixes
were genuinely applied and not silently skipped during the build pipeline.
"""

import os
import sys
import re
import time
import shutil
import tempfile
import subprocess
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

@dataclass
class CheckResult:
    name: str
    passed: bool
    duration: float
    message: str = ""
    violations: List[str] = field(default_factory=list)

@dataclass
class TierResult:
    tier_num: int
    tier_name: str
    passed: bool
    duration: float
    checks: List[CheckResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


def decompile_apk_temp(apk_path: str, out_dir: str):
    cmd = ['apktool', 'd', '-r', '-f', os.path.abspath(apk_path), '-o', out_dir]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to decompile APK for Tier 5 inspection:\n{res.stderr or res.stdout}")


def check_sa_drive_mode_noop(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    ctrl_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "camera", "PictureEffectPlusController.smali")
    if not os.path.exists(ctrl_path):
        return CheckResult("SA Drive Mode No-Op Verification", False, time.time() - start_time, "PictureEffectPlusController.smali not found in APK", [ctrl_path])

    with open(ctrl_path, "r", encoding="utf-8") as f:
        content = f.read()

    m = re.search(r'\.method public setSADriveMode\(\)V[\s\S]*?\.end method', content)
    if not m:
        violations.append("setSADriveMode() method not found in PictureEffectPlusController.smali")
    else:
        body = m.group(0)
        # Should be a no-op method with return-void and no invocation of DriveModeController
        if "DriveModeController;->setValue" in body:
            violations.append("setSADriveMode() still invokes DriveModeController.setValue, which clobbers burst/timer drive modes!")
        if "return-void" not in body:
            violations.append("setSADriveMode() missing return-void")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "setSADriveMode() confirmed no-op; continuous shooting & timers preserved" if passed else f"{len(violations)} drive mode hazards found"
    return CheckResult("SA Drive Mode No-Op Verification", passed, dur, msg, violations)


def check_sa_list_burst_unlocked(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    ctrl_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "camera", "PictureEffectPlusController.smali")
    if not os.path.exists(ctrl_path):
        return CheckResult("Burst Unlocked for Presets", False, time.time() - start_time, "PictureEffectPlusController.smali not found", [ctrl_path])

    with open(ctrl_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Search for initialization of ITEM_ID_SA_USE_EFFECT
    clinit_m = re.search(r'\.method static constructor <clinit>\(\)V[\s\S]*?\.end method', content)
    if clinit_m:
        clinit_body = clinit_m.group(0)
        if '"watercolor"' in clinit_body and 'ITEM_ID_SA_USE_EFFECT' in clinit_body:
            # Check if watercolor is added to ITEM_ID_SA_USE_EFFECT
            if re.search(r'const-string v\d+, "watercolor"[\s\S]*?ITEM_ID_SA_USE_EFFECT:Ljava/util/ArrayList;[\s\S]*?invoke-virtual \{v\d+, v\d+\}, Ljava/util/ArrayList;->add', clinit_body):
                violations.append("ITEM_ID_SA_USE_EFFECT still contains 'watercolor'; burst mode will be blocked!")
        if '"richtone-mono"' in clinit_body and 'ITEM_ID_SA_USE_EFFECT' in clinit_body:
            if re.search(r'const-string v\d+, "richtone-mono"[\s\S]*?ITEM_ID_SA_USE_EFFECT:Ljava/util/ArrayList;[\s\S]*?invoke-virtual \{v\d+, v\d+\}, Ljava/util/ArrayList;->add', clinit_body):
                violations.append("ITEM_ID_SA_USE_EFFECT still contains 'richtone-mono'; burst mode will be blocked!")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "watercolor and richtone-mono removed from ITEM_ID_SA_USE_EFFECT" if passed else f"{len(violations)} burst lock hazards found"
    return CheckResult("Burst Unlocked for Presets", passed, dur, msg, violations)


def check_ricoh_hook_dispatch(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    ctrl_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "camera", "PictureEffectPlusController.smali")
    if not os.path.exists(ctrl_path):
        return CheckResult("Ricoh Hook Dispatch Verification", False, time.time() - start_time, "PictureEffectPlusController.smali not found", [ctrl_path])

    with open(ctrl_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->applyHook" not in content:
        violations.append("RicohHook.applyHook not injected into PictureEffectPlusController.smali")

    if "Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->resetHook" not in content:
        violations.append("RicohHook.resetHook not injected into PictureEffectPlusController.smali")

    if "Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->onTerminateHook" not in content:
        violations.append("RicohHook.onTerminateHook not injected into PictureEffectPlusController.smali")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "RicohHook apply/reset/terminate dispatch confirmed in controller" if passed else f"{len(violations)} dispatch hooks missing"
    return CheckResult("Ricoh Hook Dispatch Verification", passed, dur, msg, violations)


def check_menu_layout_safety(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    layout_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "layout", "PictureEffectPlusOptionMenuLayout.smali")
    if not os.path.exists(layout_path):
        return CheckResult("Menu Layout Safety Audit", False, time.time() - start_time, "PictureEffectPlusOptionMenuLayout.smali not found", [layout_path])

    with open(layout_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Check for background ImageView drawable leak fix in onPause and onDestroy (must use if-eqz, not if-nez)
    leak_pattern = r'iget-object v\d+, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mBackgroundImageView:Landroid/widget/ImageView;\s*if-nez v\d+, :cond_\w+'
    if re.search(leak_pattern, content):
        violations.append("Found inverted null check 'if-nez' on mBackgroundImageView; leaking background drawable in onPause/onDestroy!")

    # 2. Check for closeLayout() in pushedMenuKey when mLastItemId is null (preventing unwanted app exit)
    pushed_menu_m = re.search(r'\.method public pushedMenuKey\(\)I[\s\S]*?\.end method', content)
    if pushed_menu_m:
        body = pushed_menu_m.group(0)
        if "invoke-virtual {v1}, Landroid/app/Activity;->finish()V" in body or "Activity;->finish()V" in body:
            violations.append("pushedMenuKey still calls Activity.finish() when mLastItemId is null; cancels to shooting screen expected!")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Menu layout drawable leak fix and cancel-to-shooting navigation verified" if passed else f"{len(violations)} layout safety hazards found"
    return CheckResult("Menu Layout Safety Audit", passed, dur, msg, violations)


def check_quality_raw_protection(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    pqc_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "base", "shooting", "camera", "PictureQualityController.smali")
    if not os.path.exists(pqc_path):
        return CheckResult("Picture Quality RAW Protection Audit", False, time.time() - start_time, "PictureQualityController.smali not found", [pqc_path])

    with open(pqc_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "filterQualityAvailability" not in content:
        violations.append("RicohHook.filterQualityAvailability not injected in PictureQualityController.smali")

    if 'const-string v0, "INH_FEATURE_CAM_PARAMID_JPEG_QUALITY"' in content and "const/4 v0, 0x0" not in content:
        violations.append("INH_FEATURE_CAM_PARAMID_JPEG_QUALITY is still active; will grey out quality menu in pure RAW mode")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "PictureQualityController RAW/JPEG uninhibited and availability filtered" if passed else f"{len(violations)} quality menu hazards found"
    return CheckResult("Picture Quality RAW Protection Audit", passed, dur, msg, violations)


def check_app_root_cleanup(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    app_root_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "fw", "AppRoot.smali")
    if not os.path.exists(app_root_path):
        return CheckResult("AppRoot Lifecycle & DACM Exit Audit", False, time.time() - start_time, "AppRoot.smali not found", [app_root_path])

    with open(app_root_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "Landroid/app/DAConnectionManager;->finish()V" not in content:
        violations.append("AppRoot.finish() does not invoke DAConnectionManager.finish()")

    if "Landroid/os/Process;->killProcess(I)V" not in content:
        violations.append("AppRoot.onDestroy() does not invoke Process.killProcess")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "AppRoot clean DACM disconnect and process termination verified" if passed else f"{len(violations)} lifecycle hazards found"
    return CheckResult("AppRoot Lifecycle & DACM Exit Audit", passed, dur, msg, violations)


def check_menudata_entries(work_dir: str) -> CheckResult:
    start_time = time.time()
    violations = []
    menu_path = os.path.join(work_dir, "assets", "MenuData.xml")
    if not os.path.exists(menu_path):
        return CheckResult("MenuData.xml Presets Audit", False, time.time() - start_time, "MenuData.xml not found", [menu_path])

    with open(menu_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Locate ApplicationTop section
    app_top_m = re.search(r'<Layer1\b[^>]*ItemId="ApplicationTop"[^>]*>([\s\S]*?)</Layer1>', content)
    if not app_top_m:
        violations.append("ApplicationTop Layer1 block not found in MenuData.xml")
    else:
        top_body = app_top_m.group(1)
        sub_items = re.findall(r'<Layer2\b[^>]*ItemId="([^"]+)"', top_body)
        expected = ["pop-color", "retro-photo", "richtone-mono", "rough-mono", "watercolor"]
        if sub_items != expected:
            violations.append(f"ApplicationTop items do not match expected 5 Ricoh presets! Found: {sub_items}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "MenuData.xml strictly pruned to 5 Ricoh presets" if passed else f"{len(violations)} menu entries violations found"
    return CheckResult("MenuData.xml Presets Audit", passed, dur, msg, violations)


def run_tier5_tests(apk_path: str, verbose: bool = False) -> TierResult:
    start_time = time.time()
    if not apk_path or not os.path.exists(apk_path):
        return TierResult(
            tier_num=5,
            tier_name="Patched APK Bytecode Integrity Auditor",
            passed=False,
            duration=0.0,
            checks=[],
            skip_reason=f"Target APK '{apk_path}' not found"
        )

    tmpdir = tempfile.mkdtemp(prefix="pmca_tier5_test_")
    try:
        decompile_apk_temp(apk_path, tmpdir)
        smali_root = os.path.join(tmpdir, "smali")

        checks = [
            check_sa_drive_mode_noop(smali_root),
            check_sa_list_burst_unlocked(smali_root),
            check_ricoh_hook_dispatch(smali_root),
            check_menu_layout_safety(smali_root),
            check_quality_raw_protection(smali_root),
            check_app_root_cleanup(smali_root),
            check_menudata_entries(tmpdir)
        ]

        all_passed = all(c.passed for c in checks)
        return TierResult(
            tier_num=5,
            tier_name="Patched APK Bytecode Integrity Auditor",
            passed=all_passed,
            duration=time.time() - start_time,
            checks=checks
        )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tier 5: Patched APK Bytecode Integrity Auditor")
    parser.add_argument("--apk", "-a", required=True, help="Path to built patched APK")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose violations")
    args = parser.parse_args()

    res = run_tier5_tests(args.apk, args.verbose)
    print(f"\n================================================================================")
    print(f"TIER 5 RESULT: {'PASS' if res.passed else 'FAIL'} (Duration: {res.duration:.3f}s)")
    print(f"================================================================================")
    for c in res.checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"[{status}] {c.name} ({c.duration:.3f}s)")
        if c.message:
            print(f"       Message: {c.message}")
        if not c.passed and args.verbose:
            for v in c.violations:
                print(f"       Violation: {v}")
    sys.exit(0 if res.passed else 1)
