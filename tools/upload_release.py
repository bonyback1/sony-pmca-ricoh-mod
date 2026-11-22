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

### Sony PMCA Ricoh Camera Mod v2.1.0 (B3.1) Released

This release introduces a **Live Viewfinder Preview Menu** (replacing opaque static sample PNGs with real-time EVF/LCD film simulation preview), **Refined Positive & Negative Film 3×3 Matrices**, **Fast-Path HAL Deduplication & Locale Caching**, and **UI / Logging Performance Hardening**, verified by **29/29 checks PASS** across the 5-Tier testbench!

#### 🌟 Key Highlights & Features
- **Live Viewfinder Preview Menu (`RicohHook.setupLivePreviewMenu`)**:
  - Removed the opaque black menu backdrop and disabled static sample PNG loading (`getBackgroundDrawable` / `setBackgroundResource`), exposing the live hardware EE viewfinder directly behind the preset selector.
  - Added compact translucent (`40%` black) guide strip and dark icon rail contrast backing for clear legibility over bright scenes.
  - Removed the permanently disabled `ApplicationSettings` dead item from `MenuData.xml`.
- **Calibrated Film Color Matrices & ISP Simulator Sync**:
  - Refined **Positive Film** 3×3 hardware matrix (`[991, 203, -170, -21, 1059, -14, 48, 260, 716]`) and **Negative Film** 3×3 hardware matrix (`[848, -54, 230, 169, 641, 214, 66, 278, 680]`).
  - Synced `tools/color_bench/core/isp_simulator.py` `watercolor` preset to **Leica Steve McCurry Kodachrome** (`[1118, -62, -32, -23, 1070, -23, -45, -29, 1098]`, `LB=0, CC=0`).
- **HAL Deduplication, Split Style Flags & Locale Caching**:
  - Added fast-path deduplication (`sAppliedPreset`, `sAppliedCameraHash`) in `RicohHook.applyHook()` to skip redundant HAL/DMA commits when re-applying the active preset on the same `CameraEx` instance; cleared cleanly in `resetHook()`.
  - Split user state backup flags into granular guards (`sHasSavedOriginalColorMode`, `sHasSavedOriginalTone`, `sHasSavedOriginalDRO`, `sHasSavedOriginalHDR`), eliminating monolithic try/catch fallback hazards and removing the `"standard"` overwrite fallback.
  - Cached `Locale` reference in `getLanguageType()` (`sCachedLocale`, `sCachedLangType`).
- **UI Responsiveness, Menu Ergonomics & Logging Optimization**:
  - Replaced `pushedMenuKey()` in `PictureEffectPlusOptionMenuLayout.smali` with a null-safe single-commit implementation (null-guards `mPreviousSelectedeffect`, avoids double `setValue()` on cancel, and calls `closeLayout()` cleanly).
  - Added Main Dial scrolling (`turnedMainDialNext()` / `turnedMainDialPrev()`), removed redundant double `getMenuItemDrawable()` decoding in `PictureEffectSpecialBaseMenuAdapter`, and removed duplicate `mItemNameView.setText()` calls.
  - Silenced high-frequency `AppLog` trace/debug methods (`ENABLE_LOG_DEBUG = false`, no-op `checkIf`/`enter`/`exit`/`info`/`trace`) and removed expensive exception stack walks from `getMethodName()` / `getClassName()`.
- **Automated 5-Tier Verification Testbench Expanded to 29/29 PASS**:
  - Added `check_applog_silenced` and `check_ricoh_hook_p0_hardening` to Tier 5 (`tools/testbench/test_patched_apk.py`), plus granular split-flag and dedup cache checks in Tier 2 (`tools/testbench/test_pmca_symbols.py`).
- **Inherited Core Capabilities**:
  - Full user camera state isolation & faithful restoration (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`, `DRO`, `HDR`, `LB`/`CC`).
  - Drive mode native preservation (`setSADriveMode()` no-op) & RAW mode lock elimination.
  - Full RAW + JPEG and pure RAW capture modes unlocked.
  - BIONZ X ISP hardware state sanitization & zero B&W lock.
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

### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v2.1.0 (B3.1) 发布

本版本重磅推出 **实时取景预览菜单**（告别不透明静态样张 PNG，直接在 EVF/屏幕中实时透视胶片滤镜效果）、**理光正片/负片 3×3 色彩矩阵精调**、**HAL 硬件状态去重加速与 Locale 缓存**，以及 **UI 与日志性能深度优化**，五阶自动化测试套件扩充至 **29/29 项全绿通过**！

#### 🌟 核心更新与亮点
- **实时取景预览菜单 (`RicohHook.setupLivePreviewMenu`)**:
  - 移除菜单不透明黑色背景并跳过静态样张 PNG 加载 (`getBackgroundDrawable` / `setBackgroundResource`)，直接透过菜单底层透视硬件实时取景画面；
  - 为说明栏与左侧图标列表注入 40% 半透明黑底条与暗色轨道，在强光场景下依然保持清晰文字对比度；
  - 从 `MenuData.xml` 中彻底移除永久禁用的 `ApplicationSettings` 死项。
- **精调理光胶片色彩矩阵 & ISP 模拟器同步**:
  - 精调 **理光正片 (Positive Film)** 3×3 硬件色彩矩阵 (`[991, 203, -170, -21, 1059, -14, 48, 260, 716]`) 与 **理光负片 (Negative Film)** 矩阵 (`[848, -54, 230, 169, 641, 214, 66, 278, 680]`)；
  - 同步 `tools/color_bench/core/isp_simulator.py` 第五预设位配置至 **徕卡麦凯瑞 Kodachrome** (`[1118, -62, -32, -23, 1070, -23, -45, -29, 1098]`，`LB=0, CC=0`)。
- **HAL 状态去重加速、独立参数备份标志与 Locale 缓存**:
  - 在 `RicohHook.applyHook()` 中新增快速去重路径 (`sAppliedPreset`, `sAppliedCameraHash`)，当同一 `CameraEx` 实例重复应用相同预设时直接跳过冗余 HAL/DMA 写入；在 `resetHook()` 中精准清理；
  - 将机身参数备份标志拆分为 4 个独立粒度守卫 (`sHasSavedOriginalColorMode`, `sHasSavedOriginalTone`, `sHasSavedOriginalDRO`, `sHasSavedOriginalHDR`)，彻底消除整块 try/catch 回退与 `"standard"` 误覆盖风险；
  - 在 `getLanguageType()` 中缓存 `Locale` 对象 (`sCachedLocale`, `sCachedLangType`)，避免高频字符串比较开销。
- **UI 响应速度、按键逻辑与日志静默优化**:
  - 重构 `PictureEffectPlusOptionMenuLayout.smali` 的 `pushedMenuKey()` 为单次提交安全实现（空值保护 `mPreviousSelectedeffect`，取消时不重复调用 `setValue()` 并干净执行 `closeLayout()`）；
  - 新增主拨盘滚动支持 (`turnedMainDialNext()` / `turnedMainDialPrev()`)，消除 `PictureEffectSpecialBaseMenuAdapter` 中重复的双次 `getMenuItemDrawable()` 解码及重复的 `mItemNameView.setText()` 调用；
  - 静默高频 `AppLog` 调试追踪方法 (`ENABLE_LOG_DEBUG = false`，置空 `checkIf`/`enter`/`exit`/`info`/`trace`) 并移除 `getMethodName()` / `getClassName()` 中的异常栈回溯开销。
- **五阶自动化测试工作台扩充至 29/29 项全通**:
  - Tier 5 (`tools/testbench/test_patched_apk.py`) 新增 `check_applog_silenced` 与 `check_ricoh_hook_p0_hardening` 检查；Tier 2 (`tools/testbench/test_pmca_symbols.py`) 新增独立备份标志与去重缓存审计。
- **继承特性**:
  - 机身参数状态隔离备份与无损忠实还原 (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`, `DRO`, `HDR`, `LB`/`CC`)；
  - 驱动模式原生保护 (`setSADriveMode()` 空操作) 与 RAW 模式锁定全面终结；
  - 保持 RAW+JPEG 与纯 RAW 双格式保存能力；
  - BIONZ X ISP 硬件寄存器彻底清洗与杜绝黑白锁定；
  - 兼容 PMCA 一代与二代全部微单/黑卡机型，五阶测试台 29/29 项 100% 全通。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已通过 29 项跨机型测试台验证的正式安装包（纯 V1 签名 + 4 字节对齐）。
- `Ricoh_Camera.apk`：同上安装包副本。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="繁體中文">繁體中文</h3>

### 索尼相機理光底片濾鏡模組 (Sony PMCA Ricoh Mod) v2.1.0 (B3.1) 發布

本版本重磅推出 **即時取景預覽選單**（告別不透明靜態樣張 PNG，直接在觀景窗/螢幕中即時透視底片濾鏡效果）、**理光正片/負片 3×3 色彩矩陣精調**、**HAL 硬體狀態去重加速與 Locale 快取**，以及 **UI 與日誌效能深度最佳化**，五階自動化測試套件擴充至 **29/29 項全綠通過**！

#### 🌟 核心更新與亮點
- **即時取景預覽選單 (`RicohHook.setupLivePreviewMenu`)**:
  - 移除選單不透明黑色背景並跳過靜態樣張 PNG 載入 (`getBackgroundDrawable` / `setBackgroundResource`)，直接透過選單底層透視硬體即時取景畫面；
  - 為說明欄與左側圖示列表注入 40% 半透明黑底條與暗色軌道，在強光場景下依然保持清晰文字對比度；
  - 從 `MenuData.xml` 中徹底移除永久停用的 `ApplicationSettings` 死項。
- **精調理光底片色彩矩陣 & ISP 模擬器同步**:
  - 精調 **理光正片 (Positive Film)** 3×3 硬體色彩矩陣 (`[991, 203, -170, -21, 1059, -14, 48, 260, 716]`) 與 **理光負片 (Negative Film)** 矩陣 (`[848, -54, 230, 169, 641, 214, 66, 278, 680]`)；
  - 同步 `tools/color_bench/core/isp_simulator.py` 第五預設位配置至 **徠卡麥凱瑞 Kodachrome** (`[1118, -62, -32, -23, 1070, -23, -45, -29, 1098]`，`LB=0, CC=0`)。
- **HAL 狀態去重加速、獨立參數備份旗標與 Locale 快取**:
  - 在 `RicohHook.applyHook()` 中新增快速去重路徑 (`sAppliedPreset`, `sAppliedCameraHash`)，當同一 `CameraEx` 實例重複套用相同預設時直接跳過冗餘 HAL/DMA 寫入；在 `resetHook()` 中精準清理；
  - 將機身參數備份旗標拆分為 4 個獨立粒度守衛 (`sHasSavedOriginalColorMode`, `sHasSavedOriginalTone`, `sHasSavedOriginalDRO`, `sHasSavedOriginalHDR`)，徹底消除整塊 try/catch 回退與 `"standard"` 誤覆蓋風險；
  - 在 `getLanguageType()` 中快取 `Locale` 物件 (`sCachedLocale`, `sCachedLangType`)，避免高頻字串比較開銷。
- **UI 反應速度、按鍵邏輯與日誌靜默最佳化**:
  - 重構 `PictureEffectPlusOptionMenuLayout.smali` 的 `pushedMenuKey()` 為單次提交安全實作（空值保護 `mPreviousSelectedeffect`，取消時不重複呼叫 `setValue()` 並乾淨執行 `closeLayout()`）；
  - 新增主轉盤捲動支援 (`turnedMainDialNext()` / `turnedMainDialPrev()`)，消除 `PictureEffectSpecialBaseMenuAdapter` 中重複的雙次 `getMenuItemDrawable()` 解碼及重複的 `mItemNameView.setText()` 呼叫；
  - 靜默高頻 `AppLog` 除錯追蹤方法 (`ENABLE_LOG_DEBUG = false`，置空 `checkIf`/`enter`/`exit`/`info`/`trace`) 並移除 `getMethodName()` / `getClassName()` 中的異常堆疊回溯開銷。
- **五階自動化測試工作台擴充至 29/29 項全通**:
  - Tier 5 (`tools/testbench/test_patched_apk.py`) 新增 `check_applog_silenced` 與 `check_ricoh_hook_p0_hardening` 檢查；Tier 2 (`tools/testbench/test_pmca_symbols.py`) 新增獨立備份旗標與去重快取審計。
- **繼承特性**:
  - 機身參數狀態隔離備份與無損忠實還原 (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`, `DRO`, `HDR`, `LB`/`CC`)；
  - 驅動模式原生保護 (`setSADriveMode()` 空操作) 與 RAW 模式鎖定全面終結；
  - 保持 RAW+JPEG 與純 RAW 雙格式儲存能力；
  - BIONZ X ISP 硬體暫存器徹底清洗與杜絕黑白鎖定；
  - 相容 PMCA 一代與二代全部微單眼/黑卡機型，五階測試台 29/29 項 100% 全通。

#### 📦 附件說明
- `PictureEffectPlus_Ricoh.apk`：已通過 29 項跨機型測試台驗證的正式安裝包（純 V1 簽名 + 4 位元組對齊）。
- `Ricoh_Camera.apk`：同上安裝包副本。

#### 🚀 安裝方式
```bash
./scripts/install.sh <相機IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v2.1.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B3.1) - 实时取景预览菜单 / 色彩矩阵精调 / HAL 去重加速 & 29项全通测试"
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
    parser.add_argument('--tag', default="v2.1.0", help="Release tag (default: v2.1.0)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
