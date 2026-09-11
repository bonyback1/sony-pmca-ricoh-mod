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
import struct

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

    # 2. Smart dispatch in setPlusPictureEffect: bypass resetPictureEffectSetting for Ricoh presets
    target_reset_call = 'invoke-direct {p0, p1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->resetPictureEffectSetting(Landroid/util/Pair;)V'
    if "isRicohPreset" not in content and target_reset_call in content:
        smart_dispatch = '''invoke-static {p2}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->isRicohPreset(Ljava/lang/String;)Z

    move-result v2

    if-eqz v2, :cond_ricoh_reset

    invoke-static {p0, p1, p2}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->applyHook(Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;Landroid/util/Pair;Ljava/lang/String;)Z

    const/4 v1, 0x1

    goto/16 :cond_2

    :cond_ricoh_reset
    invoke-direct {p0, p1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->resetPictureEffectSetting(Landroid/util/Pair;)V'''
        content = content.replace(target_reset_call, smart_dispatch, 1)
        print("Successfully injected smart Ricoh dispatch in setPlusPictureEffect (eliminating EVF flicker and reset IPC)")
    elif "RicohHook;->applyHook" not in content:
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

    # 5. Default backup effect to pop-color and validate in getBackupEffectValue
    target_backup = """    const-string v2, "ID_PICTUREEFFECTPLUS_CURRENT_EFFECT"

    const-string v3, "part-color-plus"

    invoke-virtual {v1, v2, v3}, Lcom/sony/imaging/app/util/BackUpUtil;->getPreferenceString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0"""

    repl_backup = """    const-string v2, "ID_PICTUREEFFECTPLUS_CURRENT_EFFECT"

    const-string v3, "pop-color"

    invoke-virtual {v1, v2, v3}, Lcom/sony/imaging/app/util/BackUpUtil;->getPreferenceString(Ljava/lang/String;Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    invoke-static {v0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getRGBMatrix(Ljava/lang/String;)[I

    move-result-object v1

    if-nez v1, :cond_ricoh_preset_ok

    const-string v0, "pop-color"

    sget-object v1, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->mBackupUtil:Lcom/sony/imaging/app/util/BackUpUtil;

    const-string v2, "ID_PICTUREEFFECTPLUS_CURRENT_EFFECT"

    invoke-virtual {v1, v2, v0}, Lcom/sony/imaging/app/util/BackUpUtil;->setPreference(Ljava/lang/String;Ljava/lang/Object;)Z

    :cond_ricoh_preset_ok"""

    if target_backup in content:
        content = content.replace(target_backup, repl_backup, 1)
        print("Successfully injected Ricoh preset validation & persistent cleanup in getBackupEffectValue()")
    else:
        print("Warning: target_backup not found in PictureEffectPlusController.smali")

    with open(controller_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched PictureEffectPlusController.smali")

def patch_base_menu_service_smali(bms_path):
    print(f"Patching {bms_path}...")
    with open(bms_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Hook getMenuItemText
    if "RicohHook;->getFilterName" not in content:
        pat_text = r'(\.method public getMenuItemText\(Ljava/lang/String;\)Ljava/lang/CharSequence;[\s\S]*?\.prologue\s*)'
        repl_text = r'''\1invoke-static {p1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getFilterName(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    if-eqz v0, :cond_ricoh_name_skip

    return-object v0

    :cond_ricoh_name_skip
    '''
        content, c = re.subn(pat_text, repl_text, content, count=1)
        if c > 0:
            print("Successfully hooked getMenuItemText in BaseMenuService.smali")
        else:
            print("Warning: Could not hook getMenuItemText in BaseMenuService.smali")

    # 2. Hook getMenuItemGuideText
    if "RicohHook;->getFilterGuide" not in content:
        pat_guide = r'(\.method public getMenuItemGuideText\(Ljava/lang/String;\)Ljava/lang/CharSequence;[\s\S]*?\.prologue\s*)'
        repl_guide = r'''\1invoke-static {p1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook;->getFilterGuide(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v0

    if-eqz v0, :cond_ricoh_guide_skip

    return-object v0

    :cond_ricoh_guide_skip
    '''
        content, c = re.subn(pat_guide, repl_guide, content, count=1)
        if c > 0:
            print("Successfully hooked getMenuItemGuideText in BaseMenuService.smali")
        else:
            print("Warning: Could not hook getMenuItemGuideText in BaseMenuService.smali")

    with open(bms_path, 'w', encoding='utf-8') as f:
        f.write(content)

def patch_option_menu_layout_smali(layout_path):
    print(f"Patching {layout_path}...")
    with open(layout_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Default effect to pop-color (ONLY in constructor initialization)
    target_init = 'const-string v0, "part-color-plus"\n\n    iput-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mSelectedItemId:Ljava/lang/String;'
    repl_init = 'const-string v0, "pop-color"\n\n    iput-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mSelectedItemId:Ljava/lang/String;'
    if target_init in content:
        content = content.replace(target_init, repl_init, 1)
        print("Successfully set initial mSelectedItemId to 'pop-color'")
    else:
        print("Warning: target_init not found in PictureEffectPlusOptionMenuLayout.smali")

    # 2. Patch title to "理光相机"
    title_target = 'iget-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mScreenTitle:Landroid/widget/TextView;\n\n    const v1, 0x7f090028\n\n    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setText(I)V'
    title_repl = 'iget-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mScreenTitle:Landroid/widget/TextView;\n\n    const-string v1, "\\u7406\\u5149\\u76f8\\u673a"\n\n    invoke-virtual {v0, v1}, Landroid/widget/TextView;->setText(Ljava/lang/CharSequence;)V'
    if title_target in content:
        content = content.replace(title_target, title_repl)
        print("Successfully set mScreenTitle to '理光相机'")

    # 3. Patch getLastStoredValues() to prevent NullPointerException
    pat_glsv = r'\.method private getLastStoredValues\(\)V[\s\S]*?\.end method'
    repl_glsv = '''.method private getLastStoredValues()V
    .locals 3

    .prologue
    iget-object v1, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->data:Landroid/os/Bundle;

    if-eqz v1, :cond_ricoh_null

    const-string v2, "MenuData"

    invoke-virtual {v1, v2}, Landroid/os/Bundle;->getParcelable(Ljava/lang/String;)Landroid/os/Parcelable;

    move-result-object v0

    check-cast v0, Lcom/sony/imaging/app/base/menu/MenuDataParcelable;

    if-nez v0, :cond_ricoh_chk

    goto :cond_ricoh_null

    :cond_ricoh_chk
    const-string v1, "back"

    invoke-virtual {v0}, Lcom/sony/imaging/app/base/menu/MenuDataParcelable;->getItemId()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v1, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v1

    if-nez v1, :cond_0

    :cond_ricoh_null
    invoke-direct {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->setPreviousMenuID()V

    iget-object v1, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mController:Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;

    invoke-virtual {v1}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getBackupEffectValue()Ljava/lang/String;

    move-result-object v1

    iput-object v1, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mPreviousSelectedeffect:Ljava/lang/String;

    :cond_0
    return-void
.end method'''
    content, c_glsv = re.subn(pat_glsv, repl_glsv, content, count=1)
    if c_glsv > 0:
        print("Successfully patched getLastStoredValues() with null safety")

    # 4. Patch setPreviousMenuID() to guard null mLastItemId
    pat_spmid = r'\.method private setPreviousMenuID\(\)V[\s\S]*?\.end method'
    repl_spmid = '''.method private setPreviousMenuID()V
    .locals 2

    .prologue
    iget-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mService:Lcom/sony/imaging/app/base/menu/BaseMenuService;

    invoke-virtual {v0}, Lcom/sony/imaging/app/base/menu/BaseMenuService;->popMenuHistory()Lcom/sony/imaging/app/base/menu/HistoryItem;

    move-result-object v0

    iput-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mLastItemId:Lcom/sony/imaging/app/base/menu/HistoryItem;

    if-eqz v0, :cond_ricoh_skip_push

    iget-object v0, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mService:Lcom/sony/imaging/app/base/menu/BaseMenuService;

    iget-object v1, p0, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->mLastItemId:Lcom/sony/imaging/app/base/menu/HistoryItem;

    invoke-virtual {v0, v1}, Lcom/sony/imaging/app/base/menu/BaseMenuService;->pushMenuHistory(Lcom/sony/imaging/app/base/menu/HistoryItem;)V

    :cond_ricoh_skip_push
    return-void
.end method'''
    content, c_spmid = re.subn(pat_spmid, repl_spmid, content, count=1)
    if c_spmid > 0:
        print("Successfully patched setPreviousMenuID() with null check")

    # 5. Patch pushedMenuKey() to call closeLayout() when mLastItemId is null
    menu_exit_target = """    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->getActivity()Landroid/app/Activity;

    move-result-object v1

    invoke-virtual {v1}, Landroid/app/Activity;->finish()V"""
    menu_exit_repl = """    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->closeLayout()V"""
    if menu_exit_target in content:
        content = content.replace(menu_exit_target, menu_exit_repl)
        print("Successfully patched pushedMenuKey() to closeLayout() back to shooting")

    # 6. Patch pushedRightKey() and pushedLeftKey()
    pat_right = r'\.method public pushedRightKey\(\)I[\s\S]*?\.end method'
    repl_right = '''.method public pushedRightKey()I
    .locals 1

    .prologue
    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->pushedDownKey()I

    move-result v0

    return v0
.end method'''
    content, c_right = re.subn(pat_right, repl_right, content, count=1)
    if c_right > 0:
        print("Successfully mapped pushedRightKey() to pushedDownKey() (move next)")

    pat_left = r'\.method public pushedLeftKey\(\)I[\s\S]*?\.end method'
    repl_left = '''.method public pushedLeftKey()I
    .locals 1

    .prologue
    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->pushedUpKey()I

    move-result v0

    return v0
.end method'''
    content, c_left = re.subn(pat_left, repl_left, content, count=1)
    if c_left > 0:
        print("Successfully mapped pushedLeftKey() to pushedUpKey() (move prev)")

    # 7. Add turnedMainDialNext() and turnedMainDialPrev()
    if "turnedMainDialNext()I" not in content:
        main_dial_methods = '''
.method public turnedMainDialNext()I
    .locals 1

    .prologue
    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->pushedDownKey()I

    move-result v0

    return v0
.end method

.method public turnedMainDialPrev()I
    .locals 1

    .prologue
    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->pushedUpKey()I

    move-result v0

    return v0
.end method
'''
        content += main_dial_methods
        print("Successfully added turnedMainDialNext() and turnedMainDialPrev()")

    # 8. Patch turnedSubDialNext() and turnedSubDialPrev() to directly call pushedDownKey() and pushedUpKey()
    pat_sub_next = r'(\.method public turnedSubDialNext\(\)I[\s\S]*?)invoke-super \{p0\}, Lcom/sony/imaging/app/base/menu/layout/SpecialScreenMenuLayout;->turnedMainDialNext\(\)I'
    repl_sub_next = r'\1invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->pushedDownKey()I'
    content, c_snext = re.subn(pat_sub_next, repl_sub_next, content, count=1)
    if c_snext > 0:
        print("Successfully mapped turnedSubDialNext() to pushedDownKey() (move next)")

    pat_sub_prev = r'(\.method public turnedSubDialPrev\(\)I[\s\S]*?)invoke-super \{p0\}, Lcom/sony/imaging/app/base/menu/layout/SpecialScreenMenuLayout;->turnedMainDialPrev\(\)I'
    repl_sub_prev = r'\1invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/layout/PictureEffectPlusOptionMenuLayout;->pushedUpKey()I'
    content, c_sprev = re.subn(pat_sub_prev, repl_sub_prev, content, count=1)
    if c_sprev > 0:
        print("Successfully mapped turnedSubDialPrev() to pushedUpKey() (move prev)")

    with open(layout_path, 'w', encoding='utf-8') as f:
        f.write(content)

def patch_ee_state_smali(ee_state_path):
    print(f"Patching {ee_state_path}...")
    with open(ee_state_path, 'r', encoding='utf-8') as f:
        content = f.read()

    target = """    invoke-static {}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getInstance()Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;

    move-result-object v0

    invoke-virtual {v0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->forceEffectOptionSetting()V"""

    repl = """    invoke-static {}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getInstance()Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;

    move-result-object v0

    invoke-virtual {v0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->forceEffectSetting()V

    invoke-static {}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->getInstance()Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;

    move-result-object v0

    invoke-virtual {v0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/camera/PictureEffectPlusController;->forceEffectOptionSetting()V"""

    if target in content and "forceEffectSetting" not in content:
        content = content.replace(target, repl, 1)
        print("Successfully injected forceEffectSetting() in PictureEffectEEState.onResume()")
    else:
        print("Notice: forceEffectSetting() already present or target not found in PictureEffectEEState.smali")

    with open(ee_state_path, 'w', encoding='utf-8') as f:
        f.write(content)

def patch_app_root_smali(app_root_path):
    print(f"Patching {app_root_path}...")
    with open(app_root_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Patch finish(Lcom/sony/imaging/app/fw/AppRoot$FINISH_TYPE;)V
    pat_finish = r'\.method public finish\(Lcom/sony/imaging/app/fw/AppRoot\$FINISH_TYPE;\)V[\s\S]*?\.end method'
    repl_finish = '''.method public finish(Lcom/sony/imaging/app/fw/AppRoot$FINISH_TYPE;)V
    .locals 7
    .param p1, "type"    # Lcom/sony/imaging/app/fw/AppRoot$FINISH_TYPE;

    .prologue
    const-string v1, "DLApp Shutdown"

    invoke-static {v1}, Lcom/sony/imaging/app/util/PTag;->start(Ljava/lang/String;)V

    :try_start_0
    const/4 v0, 0x0

    new-array v5, v0, [Ljava/lang/String;

    new-array v6, v0, [Ljava/lang/String;

    const-string v3, ""

    const-string v4, ""

    const-string v1, "com.sony.scalar.dlsys.scalaralauncher"

    const-string v2, "com.sony.scalar.dlsys.scalaralauncher.ScalarALauncher"

    move-object v0, p0

    invoke-static/range {v0 .. v6}, Lcom/sony/imaging/app/util/AppInfo;->notifyAppInfo(Landroid/content/Context;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;[Ljava/lang/String;[Ljava/lang/String;)V

    new-instance v0, Landroid/app/DAConnectionManager;

    invoke-direct {v0, p0}, Landroid/app/DAConnectionManager;-><init>(Landroid/content/Context;)V

    invoke-virtual {v0}, Landroid/app/DAConnectionManager;->finish()V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    :goto_0
    invoke-super {p0}, Landroid/app/Activity;->finish()V

    const/4 v1, 0x3

    invoke-static {v1}, Lcom/sony/imaging/app/fw/RunStatus;->setStatus(I)V

    return-void

    :catch_0
    move-exception v0

    goto :goto_0
.end method'''

    new_content, c1 = re.subn(pat_finish, repl_finish, content, count=1)
    if c1 > 0:
        print("Successfully patched AppRoot.finish(FINISH_TYPE) with clean DACM exit & Activity.finish()")
    else:
        print("Warning: Could not patch AppRoot.finish(FINISH_TYPE)")

    # 2. Patch onDestroy()V
    pat_destroy = r'\.method protected final onDestroy\(\)V[\s\S]*?\.end method'
    repl_destroy = '''.method protected final onDestroy()V
    .locals 1

    .prologue
    invoke-super {p0}, Landroid/app/Activity;->onDestroy()V

    invoke-static {}, Landroid/os/Process;->myPid()I

    move-result v0

    invoke-static {v0}, Landroid/os/Process;->killProcess(I)V

    return-void
.end method'''

    new_content, c2 = re.subn(pat_destroy, repl_destroy, new_content, count=1)
    if c2 > 0:
        print("Successfully patched AppRoot.onDestroy() with process kill")
    else:
        print("Warning: Could not patch AppRoot.onDestroy()")

    with open(app_root_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

def patch_key_handler_smali(key_handler_path):
    print(f"Patching {key_handler_path}...")
    with open(key_handler_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add pushedEnter5WayFuncKey and pushedEnterJoyStickFuncKey if not present
    if 'pushedEnter5WayFuncKey' not in content:
        extra_methods = '''
.method public pushedEnter5WayFuncKey()I
    .locals 1

    .prologue
    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/trigger/PictureEffectPlusS1OffEEStateKeyHandler;->pushedCenterKey()I

    move-result v0

    return v0
.end method

.method public pushedEnterJoyStickFuncKey()I
    .locals 1

    .prologue
    invoke-virtual {p0}, Lcom/sony/imaging/app/pictureeffectplus/shooting/trigger/PictureEffectPlusS1OffEEStateKeyHandler;->pushedCenterKey()I

    move-result v0

    return v0
.end method
'''
        content += extra_methods
        print("Successfully appended pushedEnter5WayFuncKey and pushedEnterJoyStickFuncKey to key handler")

    with open(key_handler_path, 'w', encoding='utf-8') as f:
        f.write(content)

def patch_key_converter_smali(key_converter_path):
    print(f"Patching {key_converter_path}...")
    with open(key_converter_path, 'r', encoding='utf-8') as f:
        content = f.read()

    target = """    invoke-interface {v11, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;

    move-result-object v7"""

    repl = """    invoke-interface {v11, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;

    move-result-object v7

    const/16 v11, 0xe8

    if-ne v2, v11, :cond_ricoh_not_center

    const/4 v7, 0x0

    :cond_ricoh_not_center"""

    if target in content:
        content = content.replace(target, repl, 1)
        print("Successfully patched KeyConverter.smali: scanCode 0xe8 (Center Button) bypasses custom key intercept -> pushedCenterKey()")
    else:
        print("Warning: target invoke-interface mCustomKeyMgr not found in KeyConverter.smali")

    with open(key_converter_path, 'w', encoding='utf-8') as f:
        f.write(content)

def patch_resources_arsc(arsc_path):
    print(f"Patching {arsc_path}...")
    with open(arsc_path, 'rb') as f:
        data = bytearray(f.read())

    res_type, header_size, file_size, pkg_cnt = struct.unpack('<HHII', data[:12])
    sp_offset = header_size
    sp_type, sp_hdr_size, sp_chunk_size, str_cnt, sty_cnt, flags, str_start, sty_start = struct.unpack('<HHIIIIII', data[sp_offset:sp_offset+28])
    offsets = struct.unpack(f'<{str_cnt}I', data[sp_offset+28 : sp_offset+28+4*str_cnt])
    strings_data_start = sp_offset + str_start

    strings = []
    for idx in range(str_cnt):
        s_ptr = strings_data_start + offsets[idx]
        u16len = data[s_ptr]
        s_ptr += 1
        if u16len & 0x80:
            u16len = ((u16len & 0x7f) << 8) | data[s_ptr]
            s_ptr += 1
        u8len = data[s_ptr]
        s_ptr += 1
        if u8len & 0x80:
            u8len = ((u8len & 0x7f) << 8) | data[s_ptr]
            s_ptr += 1
        s_bytes = data[s_ptr : s_ptr + u8len]
        strings.append(s_bytes.decode('utf-8', errors='replace'))

    target_names = {
        'Picture Effect+', 'Picture\nEffect+', '照片效果+', '照片\n效果+',
        '相片效果+', '相片\n效果+', 'ピクチャーエフェクト＋', 'ピクチャー\nエフェクト＋',
        'Эффект\nрисунка+', 'Foto\nefekat+', 'جلوه تصویر+', 'Kép effektus+',
        'Kesan\nGambar+', 'Εφέ φωτογραφ.+', 'Effet photo+', 'Efeito Foto+',
        'Kuvateh.+', 'Effet de\nphoto+', 'Efek Gambar+', 'Efekt\nwizualny+',
        'Efeito\nFoto+', 'Resim\nEfekti+', 'เอฟเฟ็คของภาพ+', 'Effetto\nimmagine+',
        'Kesan Gambar+', 'Hiệu ứng Hình ảnh+', 'Efect\nimagine+', 'Obrazový\nefekt+',
        '사진 효과+', 'เอฟเฟ็ค\nของภาพ+', 'Resim Efekti+', 'Эффект рисунка+',
        'Ефект малюнка+', 'Obrazový efekt+', 'تأثير الصورة+', 'Bildeeffekt+',
        'Bildeffekt+', 'Foto efekat+', 'Billedeffekt+', 'Efeito de Imagem+',
        'Εφέ\nφωτογραφ.+', 'Billed-\neffekt+', 'Фотоефект+', 'Efecto de\nfoto+',
        'Ефект\nмалюнка+', 'Foto-effect+', 'Efeito de\nImagem+', 'Efekt wizualny+',
        'Effetto immagine+', 'Bilde-\neffekt+', 'Hiệu ứng\nHình ảnh+', 'Efect imagine+',
        'Effet de photo+', 'Efecto de foto+'
    }

    replaced_count = 0
    for idx in range(len(strings)):
        if strings[idx] in target_names:
            strings[idx] = '理光相机'
            replaced_count += 1

    print(f"Replaced {replaced_count} localized app titles in resources.arsc with '理光相机'")

    def encode_str(s):
        u8 = s.encode('utf-8')
        u16_len = len(s)
        u8_len = len(u8)
        buf = bytearray()
        if u16_len > 0x7f:
            buf.append((u16_len >> 8) | 0x80)
            buf.append(u16_len & 0xff)
        else:
            buf.append(u16_len)
        if u8_len > 0x7f:
            buf.append((u8_len >> 8) | 0x80)
            buf.append(u8_len & 0xff)
        else:
            buf.append(u8_len)
        buf.extend(u8)
        buf.append(0)
        return bytes(buf)

    repacked_str_data = bytearray()
    repacked_offsets = []
    for s in strings:
        repacked_offsets.append(len(repacked_str_data))
        repacked_str_data.extend(encode_str(s))

    while len(repacked_str_data) % 4 != 0:
        repacked_str_data.append(0)

    new_sp_chunk_size = str_start + len(repacked_str_data)
    diff = new_sp_chunk_size - sp_chunk_size

    new_offsets_bytes = struct.pack(f'<{str_cnt}I', *repacked_offsets)
    new_sp_chunk = bytearray()
    new_sp_chunk.extend(struct.pack('<HHIIIIII', sp_type, sp_hdr_size, new_sp_chunk_size, str_cnt, sty_cnt, flags, str_start, sty_start))
    new_sp_chunk.extend(new_offsets_bytes)
    while len(new_sp_chunk) < str_start:
        new_sp_chunk.append(0)
    new_sp_chunk.extend(repacked_str_data)

    rest_of_data = data[sp_offset + sp_chunk_size:]
    new_file_size = file_size + diff
    new_header = struct.pack('<HHII', res_type, header_size, new_file_size, pkg_cnt)

    final_data = new_header + new_sp_chunk + rest_of_data
    with open(arsc_path, 'wb') as f:
        f.write(final_data)
    print("Successfully patched resources.arsc string pool!")

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

    # Reset default effect to "pop-color" on cold launcher boot
    target_boot = """:pswitch_0
    invoke-static {v5}, Lcom/sony/imaging/app/pictureeffectplus/shooting/PictureEffectEEState;->setIsMenuStateAdd(Z)V"""

    repl_boot = """:pswitch_0
    invoke-static {v5}, Lcom/sony/imaging/app/pictureeffectplus/shooting/PictureEffectEEState;->setIsMenuStateAdd(Z)V

    invoke-static {}, Lcom/sony/imaging/app/util/BackUpUtil;->getInstance()Lcom/sony/imaging/app/util/BackUpUtil;

    move-result-object v3

    const-string v4, "ID_PICTUREEFFECTPLUS_CURRENT_EFFECT"

    const-string v0, "pop-color"

    invoke-virtual {v3, v4, v0}, Lcom/sony/imaging/app/util/BackUpUtil;->setPreference(Ljava/lang/String;Ljava/lang/Object;)Z"""

    if target_boot in content and "ID_PICTUREEFFECTPLUS_CURRENT_EFFECT" not in content:
        content = content.replace(target_boot, repl_boot, 1)
        with open(app_smali_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully injected cold boot pop-color reset in PictureEffectPlus.smali (BootFactor.LUNCHER)")

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
        print("==> [3/7] Patching Smali controller, menu service, layout, key handlers, and AppRoot ...")
        ctrl_smali = os.path.join(target_hook_dir, 'PictureEffectPlusController.smali')
        if not os.path.exists(ctrl_smali):
            raise FileNotFoundError(f"Controller smali not found at {ctrl_smali}")
        patch_controller_smali(ctrl_smali)

        bms_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'base', 'menu', 'BaseMenuService.smali')
        if os.path.exists(bms_smali):
            patch_base_menu_service_smali(bms_smali)
        else:
            print("Warning: BaseMenuService.smali not found, skipping menu service patch.")

        layout_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'pictureeffectplus', 'shooting', 'layout', 'PictureEffectPlusOptionMenuLayout.smali')
        if os.path.exists(layout_smali):
            patch_option_menu_layout_smali(layout_smali)

        ee_state_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'pictureeffectplus', 'shooting', 'PictureEffectEEState.smali')
        if os.path.exists(ee_state_smali):
            patch_ee_state_smali(ee_state_smali)
        else:
            print("Warning: PictureEffectEEState.smali not found, skipping EEState patch.")

        app_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'pictureeffectplus', 'PictureEffectPlus.smali')
        if os.path.exists(app_smali):
            patch_app_name_smali(app_smali)

        app_root_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'fw', 'AppRoot.smali')
        if os.path.exists(app_root_smali):
            patch_app_root_smali(app_root_smali)
        else:
            print("Warning: AppRoot.smali not found, skipping AppRoot patch.")

        key_handler_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'pictureeffectplus', 'shooting', 'trigger', 'PictureEffectPlusS1OffEEStateKeyHandler.smali')
        if os.path.exists(key_handler_smali):
            patch_key_handler_smali(key_handler_smali)
        else:
            print("Warning: PictureEffectPlusS1OffEEStateKeyHandler.smali not found, skipping key handler patch.")

        key_converter_smali = os.path.join(work_dir, 'smali', 'com', 'sony', 'imaging', 'app', 'fw', 'KeyConverter.smali')
        if os.path.exists(key_converter_smali):
            patch_key_converter_smali(key_converter_smali)
        else:
            print("Warning: KeyConverter.smali not found, skipping key converter patch.")

        # Step 4: Update MenuData.xml
        print("==> [4/7] Updating filter names in MenuData.xml ...")
        menu_xml = os.path.join(work_dir, 'assets', 'MenuData.xml')
        if os.path.exists(menu_xml):
            update_menu_data(menu_xml)
        else:
            print("Warning: assets/MenuData.xml not found, skipping menu update.")

        # Step 5: Patch resources.arsc string pool
        print("==> [5/7] Patching resources.arsc string pool for app display name ...")
        arsc_file = os.path.join(work_dir, 'resources.arsc')
        if os.path.exists(arsc_file):
            patch_resources_arsc(arsc_file)
        else:
            print("Warning: resources.arsc not found, skipping arsc patch.")

        # Step 6: Rebuild APK
        print("==> [6/7] Rebuilding APK with apktool ...")
        unsigned_apk = os.path.join(work_dir, 'unsigned.apk')
        run_cmd(['apktool', 'b', work_dir, '-o', unsigned_apk])

        # Step 7: Sign APK
        print(f"==> [7/7] Signing APK -> {output_apk} ...")
        uber_jar = os.path.join(PROJECT_ROOT, 'tools', 'uber-apk-signer.jar')
        if not os.path.exists(uber_jar) and os.path.exists('/tmp/uber-apk-signer.jar'):
            uber_jar = '/tmp/uber-apk-signer.jar'

        signed = False
        java_candidates = [
            '/opt/homebrew/Cellar/openjdk/26.0.2.1/libexec/openjdk.jdk/Contents/Home/bin/java',
            '/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home/bin/java',
            '/opt/homebrew/bin/java',
            shutil.which('java')
        ]
        java_bin = None
        for jc in java_candidates:
            if jc and os.path.isfile(jc) and os.access(jc, os.X_OK):
                # Verify java actually works
                try:
                    res = subprocess.run([jc, '-version'], capture_output=True)
                    if res.returncode == 0:
                        java_bin = jc
                        break
                except Exception:
                    pass

        if os.path.exists(uber_jar) and java_bin:
            try:
                shutil.copyfile(unsigned_apk, output_apk)
                run_cmd([java_bin, '-jar', uber_jar, '-a', os.path.abspath(output_apk), '--overwrite', '--allowResign'])
                print(f"Successfully signed with uber-apk-signer -> {output_apk}")
                signed = True
            except Exception as e:
                print(f"uber-apk-signer failed ({e}), falling back to sign_apk...")

        if not signed:
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
