#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Release Publisher for Sony PMCA Ricoh Camera Mod.
Uploads APK binary assets to GitHub Releases using GitHub REST API.
"""

import os
import sys
import json
import urllib.request
import urllib.error
import argparse

REPO = "bonyback1/sony-pmca-ricoh-mod"
API_URL = f"https://api.github.com/repos/{REPO}/releases"

DEFAULT_BODY = """<p align="center">
  <strong><a href="#english">English</a></strong> |
  <strong><a href="#简体中文">简体中文</a></strong> |
  <strong><a href="#繁體中文">繁體中文</a></strong>
</p>

---

<h3 id="english">English</h3>

### Sony PMCA Ricoh Camera Mod v2.0.0 (B3.0) Released

This milestone release introduces **Full User Camera State Isolation & Restoration**, **Drive Mode Native Preservation (Zero Clobbering)**, **Complete RAW Mode Lock Elimination**, and a brand-new **5-Tier Automated Verification Testbench (27/27 Checks PASS)**!

#### 🌟 Key Highlights & Features
- **User Camera State Isolation & Faithful Restoration**:
  - Automatically captures and backs up the user's pre-existing Creative Style (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`), Dynamic Range Optimizer (`DRO`), High Dynamic Range (`HDR`), and live White Balance (`LB`/`CC` shifts) from `CameraSetting.getParameters()`.
  - Faithfully restores all original parameters back into hardware registers on `resetHook` / app exit, preventing cross-session camera setting drift.
- **Drive Mode Native Preservation (Zero Clobbering)**:
  - Neutralized `PictureEffectPlusController.setSADriveMode()` into a pure `return-void` no-op, preventing the app from resetting the user's continuous burst or timer drive modes when toggling effects menus.
- **RAW Mode Lock Elimination & Seamless Dual Format**:
  - Overrode `PictureEffectPlusController.getAvailableValue()` with `getSupportedValue()`, ensuring all 5 presets remain available and selectable even in pure RAW mode.
  - Forced `PictureEffectPlusController.isAvailable()` and neutralized `isUnavailableSceneFactor()`, keeping the filter menu active and preserving the viewfinder OSD icon in RAW mode.
  - Neutralized `INH_FEATURE_CAM_PARAMID_JPEG_QUALITY` in `PictureQualityController.isAvailable()`, preventing quality settings from becoming locked or greyed out.
  - Patched `filterQualityAvailability` to permit all format transitions, and guarded `Still_ImageSize` restoration against empty strings.
  - Patched `PictureEffectController.createSupportedModeArray()` to guarantee `watercolor` (Steve McCurry Kodachrome) availability across all camera hardware revisions.
- **Lifecycle Safety, Memory Leak Fixes & Strict Patch Pipeline**:
  - Fixed inverted null check (`if-nez` -> `if-eqz`) on `mBackgroundImageView` in `onPause()` and `onDestroy()`, eliminating bitmap drawable leaks across repeated menu toggles.
  - Patched `setFoooterGuide()` to display standard Return navigation instead of "Exit Application" when launched via Center Key.
  - Enforced Strict Patch Mode in `tools/patch_apk.py`: aborts build instantly with explicit failure reports if any official Smali modification fails.
- **Automated 5-Tier Verification Testbench (27/27 PASS)**:
  - Introduced **Tier 5: Patched APK Bytecode Integrity Auditor** (`tools/testbench/test_patched_apk.py`), decompiling the built APK to audit Dalvik bytecode directly for all hooks, drive mode no-ops, lifecycle cleanups, and menu schemas.
  - Total automated verification expanded from 20 to **27 checks (100% PASS)**.
- **Inherited Core Capabilities**:
  - Full RAW + JPEG and pure RAW capture modes unlocked.
  - BIONZ X ISP hardware state sanitization & zero B&W lock (`setColorSelectMode("off")` & 3x3 identity matrix).
  - Authentic Ricoh GR III 3D LUT decomposition (Positive Film, Negative Film, High Contrast B&W) & Moriyama Daido style.
  - Authentic Leica Steve McCurry Kodachrome documentary film profile.
  - Pixel-perfect native UI icons (70x60) & calibrated 280x480 preview assets.
  - Universal PMCA cross-generation compatibility (A7, A6000, A6300, A6500, A7M2, A7R2, RX100 series).

#### 📦 Attachments
- `PictureEffectPlus_Ricoh.apk`: Production signed release APK (Pure V1 JAR signature + 4-byte ZipAlign).
- `Ricoh_Camera.apk`: Exact mirror of the production APK.

#### 🚀 Installation
```bash
./scripts/install.sh <CAMERA_IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="简体中文">简体中文</h3>

### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v2.0.0 (B3.0) 重磅发布

本里程碑版本带来 **机身参数状态隔离备份与无损忠实还原**、**驱动模式原生保护 (杜绝参数被篡改)**、**RAW 模式锁定全面终结** 以及全新的 **五阶自动化跨机型测试套件 (27/27 项全绿通过)**！

#### 🌟 核心更新与亮点
- **机身参数状态隔离备份与无损忠实还原**:
  - 首次应用滤镜时，从底层活跃 `CameraSetting.getParameters()` 捕获并备份用户原有的创意风格 (`ColorMode`)、对比度 (`Contrast`)、饱和度 (`Saturation`)、锐度 (`Sharpness`)、动态范围优化 (`DRO`) 与高动态范围 (`HDR`)；
  - 升级白平衡备份逻辑，直接从活跃 `CameraSetting` 获取 `LB` 与 `CC` 偏置，杜绝从空参数读取导致的未初始化问题；
  - 退出应用 (`resetHook`) 时将上述参数 100% 忠实还原至底层硬件寄存器，彻底杜绝滤镜使用后机身参数漂移或被覆盖为默认值。
- **驱动模式原生保护 (杜绝参数被篡改)**:
  - 将 `PictureEffectPlusController.setSADriveMode()` 彻底重构为 `return-void` 空操作，彻底根治关闭或退出滤镜菜单时驱动模式被强制重置为单张拍摄的原生缺陷。
- **RAW 模式锁定全面终结与纯净双格式**:
  - 重写 `PictureEffectPlusController.getAvailableValue()`，改为调用 `getSupportedValue()`，确保即使在纯 RAW 模式下 5 款理光预设依然完全可选；
  - 强制 `PictureEffectPlusController.isAvailable()` 返回真，并中和 `isUnavailableSceneFactor()`，实现 RAW 模式下取景 OSD 滤镜图标常驻且滤镜菜单自由进入；
  - 中和 `PictureQualityController.isAvailable()` 中的 `INH_FEATURE_CAM_PARAMID_JPEG_QUALITY` 互斥锁，确保画质选项在任何状态下皆可自由切换；
  - 优化 `filterQualityAvailability` 允许所有画质顺畅切换，并增加 `Still_ImageSize` 还原防空串保护；
  - 修补 `PictureEffectController.createSupportedModeArray()`，确保 `watercolor` (麦凯瑞 Kodachrome) 在所有硬件世代机型上 100% 完整支持。
- **生命周期安全、内存泄漏修复与严格构建管线**:
  - 修复 `PictureEffectPlusOptionMenuLayout` 中 `mBackgroundImageView` 的反向空指针判断缺陷 (`if-nez` -> `if-eqz`)，彻底根治反复进出菜单导致的 Drawable 位图内存泄漏；
  - 修复 `setFoooterGuide()`，由中心键唤出菜单时底部指南准确显示“返回”而非“退出应用程序”；
  - 引入严格构建模式 (Strict Patch Mode)：任何官方 Smali 修补失败立即中断编译并打印详细违规项，杜绝静默失败。
- **五阶自动化测试工作台重磅上线 (27/27 项全通)**:
  - 新增 **Tier 5: 反编译字节码完整性审计器** (`tools/testbench/test_patched_apk.py`)，直接解包检查目标 Smali 字节码，严密核验生命周期 Hook、驱动模式 No-op、内存泄漏修复与菜单结构；
  - 跨机型测试项从 20 项扩充至 **27 项全绿通过 (100% PASS)**。
- **继承特性**:
  - 突破官方限制：全套 5 款理光胶片预设全线支持高速连拍 (Hi/Mid/Lo)、速度优先连拍、定时自拍与阶段曝光；
  - 官方真·徕卡麦凯瑞纪实色彩 (`Leica_SteveMcCurry.cube` 逆向数学分解)；
  - 保持 RAW+JPEG 与纯 RAW 双格式保存能力；
  - 保持真·理光 GR3 3D LUT 正片、负片、高对比黑白与森山大道黑白色彩；
  - BIONZ X ISP 硬件寄存器彻底清洗与杜绝黑白锁定；
  - 兼容 PMCA 一代与二代全部微单/黑卡机型，五阶测试台 27/27 项 100% 全通。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已通过 27 项跨机型测试台验证的正式安装包（纯 V1 签名 + 4 字节对齐）。
- `Ricoh_Camera.apk`：同上安装包副本。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="繁體中文">繁體中文</h3>

### 索尼相機理光底片濾鏡模組 (Sony PMCA Ricoh Mod) v2.0.0 (B3.0) 重磅發布

本里程碑版本帶來 **機身參數狀態隔離備份與無損忠實還原**、**驅動模式原生保護 (杜絕參數被竄改)**、**RAW 模式鎖定全面終結** 以及全新的 **五階自動化跨機型測試套件 (27/27 項全綠通過)**！

#### 🌟 核心更新與亮點
- **機身參數狀態隔離備份與無損忠實還原**:
  - 首次套用濾鏡時，從底層活躍 `CameraSetting.getParameters()` 擷取並備份使用者原有的風格設定 (`ColorMode`)、對比度 (`Contrast`)、飽和度 (`Saturation`)、銳利度 (`Sharpness`)、動態範圍最佳化 (`DRO`) 與高動態範圍 (`HDR`)；
  - 升級白平衡備份邏輯，直接從活躍 `CameraSetting` 取得 `LB` 與 `CC` 偏移，杜絕從空參數讀取導致的未初始化問題；
  - 退出應用程式 (`resetHook`) 時將上述參數 100% 忠實還原至底層硬體暫存器，徹底杜絕濾鏡使用後機身參數漂移或被覆蓋為預設值。
- **驅動模式原生保護 (杜絕參數被竄改)**:
  - 將 `PictureEffectPlusController.setSADriveMode()` 徹底重構為 `return-void` 空操作，徹底根治關閉或退出濾鏡選單時驅動模式被強制重設為單張拍攝的原生缺陷。
- **RAW 模式鎖定全面終結與純淨雙格式**:
  - 重寫 `PictureEffectPlusController.getAvailableValue()`，改為呼叫 `getSupportedValue()`，確保即使在純 RAW 模式下 5 款理光預設依然完全可選；
  - 強制 `PictureEffectPlusController.isAvailable()` 返回真，並中和 `isUnavailableSceneFactor()`，實現 RAW 模式下取景 OSD 濾鏡圖示常駐且濾鏡選單自由進入；
  - 中和 `PictureQualityController.isAvailable()` 中的 `INH_FEATURE_CAM_PARAMID_JPEG_QUALITY` 互斥鎖，確保畫質選項在任何狀態下皆可自由切換；
  - 最佳化 `filterQualityAvailability` 允許所有畫質順暢切換，並增加 `Still_ImageSize` 還原防空字串保護；
  - 修補 `PictureEffectController.createSupportedModeArray()`，確保 `watercolor` (麥凱瑞 Kodachrome) 在所有硬體世代機型上 100% 完整支援。
- **生命週期安全、記憶體流失修復與嚴格建置管線**:
  - 修復 `PictureEffectPlusOptionMenuLayout` 中 `mBackgroundImageView` 的反向空指標判斷缺陷 (`if-nez` -> `if-eqz`)，徹底根治反覆進出選單導致的 Drawable 位圖記憶體流失；
  - 修復 `setFoooterGuide()`，由中心鍵喚出選單時底部指南準確顯示「返回」而非「退出應用程式」；
  - 引入嚴格建置模式 (Strict Patch Mode)：任何官方 Smali 修補失敗立即中斷編譯並印出詳細違規項，杜絕無聲失敗。
- **五階自動化測試工作台重磅上線 (27/27 項全通)**:
  - 新增 **Tier 5: 反編譯位元組碼完整性審計器** (`tools/testbench/test_patched_apk.py`)，直接解包檢查目標 Smali 位元組碼，嚴密核驗生命週期 Hook、驅動模式 No-op、記憶體流失修復與選單結構；
  - 跨機型測試項從 20 項擴充至 **27 項全綠通過 (100% PASS)**。
- **繼承特性**:
  - 突破官方限制：全套 5 款理光底片預設全線支援高速連拍 (Hi/Mid/Lo)、速度優先連拍、定時自拍與包圍曝光；
  - 官方真·徠卡麥凱瑞紀實色彩 (`Leica_SteveMcCurry.cube` 逆向數學分解)；
  - 保持 RAW+JPEG 與純 RAW 雙格式儲存能力；
  - 保持真·理光 GR3 3D LUT 正片、負片、高對比黑白與森山大道黑白色彩；
  - BIONZ X ISP 硬體暫存器徹底清洗與杜絕黑白鎖定；
  - 相容 PMCA 一代與二代全部微單眼/黑卡機型，五階測試台 27/27 項 100% 全通。

#### 📦 附件說明
- `PictureEffectPlus_Ricoh.apk`：已通過 27 項跨機型測試台驗證的正式安裝包（純 V1 簽名 + 4 位元組對齊）。
- `Ricoh_Camera.apk`：同上安裝包副本。

#### 🚀 安裝方式
```bash
./scripts/install.sh <相機IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v2.0.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B3.0) - 全机身状态无损还原 / 驱动模式原生保护 / RAW 无锁 & 五阶自动化测试套件"
    body = body or DEFAULT_BODY

    # 1. Check if release already exists for this tag
    tag_url = f"https://api.github.com/repos/{REPO}/releases/tags/{tag}"
    req = urllib.request.Request(tag_url, headers=headers)
    release_data = None
    try:
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode('utf-8'))
            print(f"Release for {tag} already exists (ID: {release_data['id']}).")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise

    # 2. Create release if not exists
    if not release_data:
        print(f"Creating new GitHub Release for tag {tag}...")
        payload = {
            "tag_name": tag,
            "name": title,
            "body": body,
            "draft": False,
            "prerelease": False
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(API_URL, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as resp:
            release_data = json.loads(resp.read().decode('utf-8'))
        print(f"Created Release {tag} successfully (ID: {release_data['id']})!")

    # 3. Upload APK asset
    upload_url_template = release_data['upload_url'] # e.g. https://uploads.github.com/.../assets{?name,label}
    upload_url = upload_url_template.split('{')[0]
    filename = os.path.basename(apk_path)
    final_upload_url = f"{upload_url}?name={filename}"

    print(f"Uploading {apk_path} ({os.path.getsize(apk_path)} bytes) to GitHub Release...")
    with open(apk_path, 'rb') as f:
        apk_bytes = f.read()

    upload_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/vnd.android.package-archive",
        "Content-Length": str(len(apk_bytes)),
        "User-Agent": "Sony-PMCA-Publisher"
    }

    req = urllib.request.Request(final_upload_url, data=apk_bytes, headers=upload_headers, method='POST')
    try:
        with urllib.request.urlopen(req) as resp:
            asset_info = json.loads(resp.read().decode('utf-8'))
            print(f"🎉 SUCCESS! Asset uploaded successfully!")
            print(f"Download URL: {asset_info['browser_download_url']}")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8')
        if "already_exists" in err_msg:
            print(f"Asset '{filename}' already exists in this Release.")
        else:
            raise RuntimeError(f"Failed to upload asset: {err_msg}")

    print(f"\nRelease URL: {release_data['html_url']}")

def main():
    parser = argparse.ArgumentParser(description="Publish Release to GitHub")
    parser.add_argument('-t', '--token', default=os.environ.get('GITHUB_TOKEN'), help="GitHub Personal Access Token")
    parser.add_argument('--tag', default="v2.0.0", help="Release tag (default: v2.0.0)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
