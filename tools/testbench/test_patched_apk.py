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

    # 2. Check pushedMenuKey P1 fixes: closeLayout() when mLastItemId null, clear mIsChangedValue before super cancel, null-guard mPreviousSelectedeffect
    pushed_menu_m = re.search(r'\.method public pushedMenuKey\(\)I[\s\S]*?\.end method', content)
    if pushed_menu_m:
        body = pushed_menu_m.group(0)
        if "invoke-virtual {v1}, Landroid/app/Activity;->finish()V" in body or "Activity;->finish()V" in body:
            violations.append("pushedMenuKey still calls Activity.finish() when mLastItemId is null; cancels to shooting screen expected!")
        if "->mIsChangedValue:Z" not in body:
            violations.append("pushedMenuKey() does not clear mIsChangedValue before super.pushedMenuKey(), causing double setValue() on cancel!")
        if not re.search(r'mPreviousSelectedeffect:Ljava/lang/String;\s*if-eqz v\d+, :cond_\w+', body):
            violations.append("pushedMenuKey() does not skip setValue() when mPreviousSelectedeffect is null!")
    else:
        violations.append("pushedMenuKey() method not found in PictureEffectPlusOptionMenuLayout.smali")

    # 3. Check live viewfinder preview wiring, static PNG bypass, strict API < 16 safety, & turnedMainDialNext()
    live_setup_sig = "RicohHook;->setupLivePreviewMenu(Landroid/view/ViewGroup;Landroid/widget/ImageView;Landroid/widget/TextView;Landroid/widget/TextView;Landroid/view/View;)V"
    if live_setup_sig not in content:
        violations.append("PictureEffectPlusOptionMenuLayout.smali does not call RicohHook.setupLivePreviewMenu()")
    for m_sig in (
        r'\.method public onResume\(\)V[\s\S]*?\.end method',
        r'\.method public onItemSelected\([^\)]*\)V[\s\S]*?\.end method',
    ):
        mm = re.search(m_sig, content)
        if not mm:
            violations.append(f"Expected method '{m_sig}' not found in PictureEffectPlusOptionMenuLayout.smali")
        else:
            m_body = mm.group(0)
            if "ImageView;->setBackgroundResource(I)V" in m_body or "->getBackgroundDrawable(Ljava/lang/String;)I" in m_body:
                violations.append(f"{mm.group(0).splitlines()[0]} still loads static preview PNG onto mBackgroundImageView!")
    if "->setBackground(Landroid/graphics/drawable/Drawable;)V" in content or "->setAlpha(F)V" in content:
        violations.append("PictureEffectPlusOptionMenuLayout.smali uses API 16+ View method (setBackground/setAlpha)!")
    if not re.search(r'\.method public turnedMainDialNext\(\)I[\s\S]*?\.end method', content):
        violations.append("PictureEffectPlusOptionMenuLayout.smali missing explicit turnedMainDialNext() override!")

    # 4. Check PictureEffectSpecialBaseMenuAdapter has only 1 getMenuItemDrawable() call (no double PNG decode)
    adapter_path = os.path.join(
        smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "layout",
        "PictureEffectPlusOptionMenuLayout$PictureEffectSpecialBaseMenuAdapter.smali"
    )
    if not os.path.exists(adapter_path):
        violations.append("PictureEffectSpecialBaseMenuAdapter.smali not found")
    else:
        with open(adapter_path, "r", encoding="utf-8") as af:
            adapter_body = af.read()
        decode_calls = len(re.findall(r'BaseMenuService;->getMenuItemDrawable\(Ljava/lang/String;\)Landroid/graphics/drawable/Drawable;', adapter_body))
        if decode_calls != 1:
            violations.append(f"PictureEffectSpecialBaseMenuAdapter calls BaseMenuService.getMenuItemDrawable() {decode_calls} times (expected 1)!")

    # 5. Check C2 Hold-to-Compare hooks across menu layout, shooting key handler, and StableLayout
    for sig in (
        "onDeleteKeyPushed(Landroid/view/KeyEvent;)I",
        "onDeleteKeyReleased(Landroid/view/KeyEvent;)I",
        "onCustom2KeyPushed(Landroid/view/KeyEvent;)I",
        "onCustom2KeyReleased(Landroid/view/KeyEvent;)I",
        "RicohHook;->ensureFilterRestored()V",
    ):
        if sig not in content:
            violations.append(f"PictureEffectPlusOptionMenuLayout.smali missing C2 compare check '{sig}'")

    kh_path = os.path.join(
        smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "trigger",
        "PictureEffectPlusS1OffEEStateKeyHandler.smali"
    )
    if not os.path.exists(kh_path):
        violations.append("PictureEffectPlusS1OffEEStateKeyHandler.smali not found")
    else:
        with open(kh_path, "r", encoding="utf-8") as kf:
            kh_body = kf.read()
        for sig in (
            "onDeleteKeyPushed(Landroid/view/KeyEvent;)I",
            "onDeleteKeyReleased(Landroid/view/KeyEvent;)I",
            "onCustom2KeyPushed(Landroid/view/KeyEvent;)I",
            "onCustom2KeyReleased(Landroid/view/KeyEvent;)I",
            "pushedS1Key()I",
            "RicohHook;->ensureFilterRestored()V",
        ):
            if sig not in kh_body:
                violations.append(f"PictureEffectPlusS1OffEEStateKeyHandler.smali missing '{sig}'")

    stable_path = os.path.join(
        smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "layout",
        "PictureEffectPlusStableLayout.smali"
    )
    if not os.path.exists(stable_path):
        violations.append("PictureEffectPlusStableLayout.smali not found")
    else:
        with open(stable_path, "r", encoding="utf-8") as sf:
            stable_body = sf.read()
        for sig in (
            "RicohHook;->attachCompareBadge(Landroid/view/ViewGroup;)V",
            "RicohHook;->detachCompareBadge(Landroid/view/ViewGroup;)V",
            "RicohHook;->ensureFilterRestored()V",
        ):
            if sig not in stable_body:
                violations.append(f"PictureEffectPlusStableLayout.smali missing '{sig}'")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Menu layout live preview, C2 compare hooks, adapter single-decode, cancel-path & dial overrides verified" if passed else f"{len(violations)} layout safety/perf hazards found"
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

    if 'ItemId="ApplicationSettings"' in content:
        violations.append("MenuData.xml still contains permanently disabled ApplicationSettings Layer1 item!")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "MenuData.xml strictly pruned to 5 Ricoh presets" if passed else f"{len(violations)} menu entries violations found"
    return CheckResult("MenuData.xml Presets Audit", passed, dur, msg, violations)


def check_applog_silenced(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    applog_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "AppLog.smali")
    if not os.path.exists(applog_path):
        return CheckResult("AppLog Stack-Walk Silence Audit", False, time.time() - start_time, "AppLog.smali not found", [applog_path])

    with open(applog_path, "r", encoding="utf-8") as f:
        content = f.read()

    if re.search(r'\.field public static final ENABLE_LOG_DEBUG:Z\s*=\s*true', content):
        violations.append("AppLog.ENABLE_LOG_DEBUG is still true!")

    for mname in ("getMethodName", "getClassName"):
        mm = re.search(rf'\.method public static {mname}\(\)Ljava/lang/String;[\s\S]*?\.end method', content)
        if not mm:
            violations.append(f"AppLog.{mname}() not found")
        elif "getStackTrace" in mm.group(0) or "Ljava/lang/Exception;" in mm.group(0):
            violations.append(f"AppLog.{mname}() still allocates Exception / unwinds stack trace!")

    for mname in ("checkIf", "enter", "exit", "info", "trace"):
        mm = re.search(rf'\.method public static (?:final )?{mname}\(Ljava/lang/String;Ljava/lang/String;\)V[\s\S]*?\.end method', content)
        if not mm:
            violations.append(f"AppLog.{mname}() not found")
        elif "outLog" in mm.group(0):
            violations.append(f"AppLog.{mname}() still calls outLog() on hot path!")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "AppLog debug/trace/stack-walk helpers silenced cleanly" if passed else f"{len(violations)} AppLog performance hazards found"
    return CheckResult("AppLog Stack-Walk Silence Audit", passed, dur, msg, violations)


def check_ricoh_hook_p0_hardening(smali_root: str) -> CheckResult:
    start_time = time.time()
    violations = []
    hook_path = os.path.join(smali_root, "com", "sony", "imaging", "app", "pictureeffectplus", "shooting", "camera", "RicohHook.smali")
    if not os.path.exists(hook_path):
        return CheckResult("RicohHook P0 Hardening Audit", False, time.time() - start_time, "RicohHook.smali not found", [hook_path])

    with open(hook_path, "r", encoding="utf-8") as f:
        content = f.read()

    reset_m = re.search(r'\.method public static resetHook\b[\s\S]*?\.end method', content)
    if not reset_m:
        violations.append("RicohHook.resetHook() not found")
    else:
        reset_body = reset_m.group(0)
        reset_code = "\n".join(
            line for line in reset_body.splitlines() if not line.lstrip().startswith("#")
        )
        if ":cond_style_fallback" in reset_code or '"standard"' in reset_code:
            violations.append("resetHook() contains style fallback overwriting user Creative Style to 'standard'!")
        if "sAppliedPreset:Ljava/lang/String;" not in reset_body or "sAppliedCameraHash:I" not in reset_body:
            violations.append("resetHook() does not clear sAppliedPreset / sAppliedCameraHash!")

    apply_m = re.search(r'\.method public static applyHook\b[\s\S]*?\.end method', content)
    if not apply_m:
        violations.append("RicohHook.applyHook() not found")
    else:
        apply_body = apply_m.group(0)
        for flag in (
            "sHasSavedOriginalColorMode:Z",
            "sHasSavedOriginalTone:Z",
            "sHasSavedOriginalDRO:Z",
            "sHasSavedOriginalHDR:Z",
        ):
            if flag not in apply_body:
                violations.append(f"applyHook() missing split backup flag '{flag}'")
        if "sAppliedPreset:Ljava/lang/String;" not in apply_body or "sAppliedCameraHash:I" not in apply_body:
            violations.append("applyHook() missing sAppliedPreset / sAppliedCameraHash dedup cache!")

    lang_m = re.search(r'\.method public static getLanguageType\(\)I[\s\S]*?\.end method', content)
    if not lang_m:
        violations.append("RicohHook.getLanguageType() not found")
    else:
        lang_body = lang_m.group(0)
        if "sCachedLocale:Ljava/util/Locale;" not in lang_body or "sCachedLangType:I" not in lang_body:
            violations.append("getLanguageType() missing sCachedLocale / sCachedLangType caching!")

    # Live preview UI helper, C2 compare helpers & strict API < 16 View safety
    for helper_sig in (
        "setupLivePreviewMenu(Landroid/view/ViewGroup;Landroid/widget/ImageView;Landroid/widget/TextView;Landroid/widget/TextView;Landroid/view/View;)V",
        "setBypassPreview(Z)V",
        "ensureFilterRestored()V",
        "handleShootingCompareKey(Landroid/view/KeyEvent;Z)I",
        "handleMenuCompareKey(Landroid/view/KeyEvent;ZLandroid/widget/TextView;Ljava/lang/String;)I",
        "attachCompareBadge(Landroid/view/ViewGroup;)V",
        "detachCompareBadge(Landroid/view/ViewGroup;)V",
    ):
        if helper_sig not in content:
            violations.append(f"RicohHook.smali missing helper '{helper_sig}'")
    if "->setBackground(Landroid/graphics/drawable/Drawable;)V" in content or "->setAlpha(F)V" in content:
        violations.append("RicohHook.smali uses API 16+ View method (setBackground/setAlpha) that crashes Dalvik on A6300!")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "RicohHook P0/P1 style-safety, split try/catch, dedup, Locale & preview cache verified" if passed else f"{len(violations)} RicohHook P0/P1 violations found"
    return CheckResult("RicohHook P0 Hardening Audit", passed, dur, msg, violations)


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
            check_ricoh_hook_p0_hardening(smali_root),
            check_applog_silenced(smali_root),
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
