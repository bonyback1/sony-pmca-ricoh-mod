#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-click Automated Patcher for Sony PMCA "Picture Effect+" -> "Ricoh Camera".
Decompiles official APK, injects Ricoh hardware ISP hook, patches controller,
updates MenuData.xml titles, rebuilds, and signs.
"""

import os
import sys
import shutil
import subprocess
import tempfile
import argparse
import re

# Import local tools
from update_menu_data import update_menu_data
from sign_apk import sign_apk

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_SMALI = os.path.join(PROJECT_ROOT, 'src', 'smali', 'RicohHook.smali')

def check_requirements():
    if not shutil.which('apktool'):
        raise SystemExit("Error: 'apktool' not found in PATH. Please install apktool (e.g. `brew install apktool`).")

def patch_controller_smali(controller_path):
    print(f"Patching {controller_path}...")
    with open(controller_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Reset hook injection in setMode
    if "RicohHook;->resetHook" not in content:
        # Match enter log before mMode = "off"
        pat1 = r'(invoke-static\s+\{[^}]+\},\s*Lcom/sony/imaging/app/pictureeffectplus/AppLog;->enter\(Ljava/lang/String;Ljava/lang/String;\)V\s*(?:\.line\s+\d+\s*)?sget-object\s+v\d+,\s*Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mMode:Ljava/lang/String;\s*const-string\s+v\d+,\s*"off")'
        def repl1(m):
            return 'invoke-static {p0, p1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->resetHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;)V\n\n    sget-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mMode:Ljava/lang/String;\n\n    const-string v2, "off"'
        new_content, count = re.subn(pat1, repl1, content, count=1)
        if count == 0:
            print("Warning: Could not inject RicohHook resetHook via regex. Trying fuzzy fallback...")
            # Fallback search
            sub_target = 'sget-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mMode:Ljava/lang/String;'
            if sub_target in content:
                new_content = content.replace(sub_target, 'invoke-static {p0, p1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->resetHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;)V\n    ' + sub_target, 1)
        content = new_content

    # 2. Apply hook injection in setPlusPictureEffect
    if "RicohHook;->applyHook" not in content:
        pat2 = r'(invoke-static\s+\{v\d+,\s*v\d+\},\s*Landroid/util/Log;->i\(Ljava/lang/String;Ljava/lang/String;\)I\s*(?:\.line\s+\d+\s*)?const-string\s+v2,\s*"part-color-plus")'
        repl2 = '''invoke-static {p0, p1, p2}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->applyHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;Ljava/lang/String;)Z

    move-result v2

    if-eqz v2, :cond_ricoh_skip

    const/4 v1, 0x1

    goto/16 :cond_2

    :cond_ricoh_skip
    const-string v2, "part-color-plus"'''
        new_content, count = re.subn(pat2, repl2, content, count=1)
        if count == 0:
            print("Warning: Could not inject RicohHook applyHook via regex. Trying fuzzy fallback...")
            sub_target2 = 'const-string v2, "part-color-plus"'
            if sub_target2 in content:
                new_content = content.replace(sub_target2, repl2, 1)
        content = new_content

    # 3. Add getCameraSetting() method if missing
    if "getCameraSetting()Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;" not in content:
        cam_method = '''
.method public getCameraSetting()Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;
    .locals 1

    iget-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mCamSet:Lcom/sony/imaging/app/base/shooting/camera/CameraSetting;

    return-object v0
.end method
'''
        # Insert before onTerminate
        term_idx = content.find('.method public onTerminate()V')
        if term_idx != -1:
            content = content[:term_idx] + cam_method + '\n' + content[term_idx:]
        else:
            content += cam_method

    # 4. Terminate hook injection in onTerminate
    if "RicohHook;->onTerminateHook" not in content:
        pat4 = r'(\.method public onTerminate\(\)V[\s\S]*?Lcom/sony/imaging/app/pictureeffectplus/AppLog;->enter\(Ljava/lang/String;Ljava/lang/String;\)V\s*(?:\.line\s+\d+\s*)?invoke-virtual\s+\{p0\},\s*Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getBackupEffectValue)'
        def repl4(m):
            return m.group(1).replace(
                m.group(1)[m.group(1).rfind('invoke-static'):m.group(1).rfind('invoke-virtual')],
                'invoke-static {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->onTerminateHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)V\n\n    '
            )
        new_content, count = re.subn(pat4, repl4, content, count=1)
        if count == 0:
            term_str = 'invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getBackupEffectValue()Ljava/lang/String;'
            if term_str in content:
                new_content = content.replace(term_str, 'invoke-static {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->onTerminateHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;)V\n    ' + term_str, 1)
        content = new_content

    with open(controller_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched PictureEffectPlusController.smali")

def patch_app_name_smali(app_smali_path):
    print(f"Patching {app_smali_path}...")
    with open(app_smali_path, 'r', encoding='utf-8') as f:
        content = f.read()

    target_str = r'const-string v3, "\u7406\u5149\u76f8\u673a"'
    if target_str not in content:
        pat = r'invoke-virtual\s+\{p0\},\s*Lcom/sony/imaging/app/pictureeffectplus/PictureEffectPlus;->getResources\(\)Landroid/content/res/Resources;[\s\S]*?invoke-virtual\s+\{v\d+,\s*v\d+\},\s*Landroid/content/res/Resources;->getString\(I\)Ljava/lang/String;\s*move-result-object\s+v\d+'
        repl = target_str
        content = re.sub(pat, lambda m: repl, content, count=1)
        with open(app_smali_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully updated app title to '理光相机' in PictureEffectPlus.smali")
    else:
        print("App title already patched.")

def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({' '.join(cmd)}):\n{res.stderr or res.stdout}")
    return res.stdout

def patch_apk(input_apk, output_apk, custom_key=None, keep_work_dir=False):
    check_requirements()

    if not os.path.exists(input_apk):
        raise FileNotFoundError(f"Input APK not found: {input_apk}")

    if not os.path.exists(SRC_SMALI):
        raise FileNotFoundError(f"Source smali not found: {SRC_SMALI}. Please run tools/generate_ricoh_hook.py first.")

    work_dir = tempfile.mkdtemp(prefix='sony_ricoh_patch_')
    print(f"==> Working directory: {work_dir}")

    try:
        # Step 1: Decompile (-r to keep resources intact, avoiding aapt private framework resource errors)
        print(f"==> [1/6] Decompiling {input_apk} (no-res mode) ...")
        run_cmd(['apktool', 'd', '-r', '-f', os.path.abspath(input_apk), '-o', work_dir])

        # Step 2: Inject RicohHook.smali
        print("==> [2/6] Injecting RicohHook.smali ...")
        target_hook_dir = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'pictureeffectplus', 'shooting', 'camera')
        os.makedirs(target_hook_dir, exist_ok=True)
        shutil.copyfile(SRC_SMALI, os.path.join(target_hook_dir, 'RicohHook.smali'))

        # Step 3: Patch Smali
        print("==> [3/6] Patching Smali controller and launcher ...")
        ctrl_smali = os.path.join(target_hook_dir, 'PictureEffectPlusController.smali')
        if not os.path.exists(ctrl_smali):
            raise FileNotFoundError(f"Controller smali not found at {ctrl_smali}")
        patch_controller_smali(ctrl_smali)

        app_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'pictureeffectplus', 'PictureEffectPlus.smali')
        if os.path.exists(app_smali):
            patch_app_name_smali(app_smali)

        # Step 4: Update MenuData.xml
        print("==> [4/6] Updating filter names in MenuData.xml ...")
        menu_xml = os.path.join(work_dir, 'assets', 'MenuData.xml')
        if os.path.exists(menu_xml):
            update_menu_data(menu_xml)
        else:
            print("Warning: assets/MenuData.xml not found, skipping menu update.")

        # Step 5: Rebuild APK
        print("==> [5/6] Rebuilding APK with apktool ...")
        unsigned_apk = os.path.join(work_dir, 'unsigned.apk')
        run_cmd(['apktool', 'b', work_dir, '-o', unsigned_apk])

        # Step 6: Sign APK
        print(f"==> [6/6] Signing APK -> {output_apk} ...")
        sign_apk(unsigned_apk, output_apk, pem_path=custom_key)

        print("\n" + "=" * 60)
        print("🎉 SUCCESS! Modded Ricoh Camera APK built successfully!")
        print(f"Output APK: {os.path.abspath(output_apk)}")
        print("Includes 5 Ricoh film presets:")
        print("  1. 理光 GR 正片 (Ricoh Positive Film)")
        print("  2. 理光负片    (Ricoh Negative Film)")
        print("  3. 高对比黑白  (Ricoh High Contrast B&W)")
        print("  4. 森山大道风  (Moriyama Daido Style)")
        print("  5. 正负逆冲    (Ricoh Cross Process)")
        print("\nInstall to camera using: ./scripts/install.sh <CAMERA_IP>")
        print("=" * 60 + "\n")

    finally:
        if not keep_work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="One-click Patcher: Sony Picture Effect+ -> Ricoh Camera")
    parser.add_argument('-i', '--input', required=True, help="Path to original official PictureEffectPlus.apk")
    parser.add_argument('-o', '--output', default="Ricoh_Camera.apk", help="Path to output signed APK (default: Ricoh_Camera.apk)")
    parser.add_argument('-k', '--key', default=None, help="Custom PEM signing key (auto-generated if omitted)")
    parser.add_argument('--keep', action='store_true', help="Keep temporary decompiled working directory")
    args = parser.parse_args()

    patch_apk(args.input, args.output, custom_key=args.key, keep_work_dir=args.keep)

if __name__ == '__main__':
    main()
