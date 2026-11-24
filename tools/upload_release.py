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

### Sony PMCA Ricoh Camera Mod v2.2.0 (B3.2) Released

This release introduces **Instant C2 / Delete Hold-to-Compare (Before/After)** across both the live shooting viewfinder and the live preset menu, allowing photographers to compare the original un-filtered scene against any active Ricoh film profile in real time!

#### 🌟 Key Highlights & Features
- **Instant Hold-to-Compare Original Scene (`RicohHook.setBypassPreview` / `handleShootingCompareKey` / `handleMenuCompareKey`)**:
  - Added press-and-hold **C2 / Delete** key handlers (`onDeleteKeyPushed` / `onDeleteKeyReleased` / `onCustom2KeyPushed` / `onCustom2KeyReleased`) to both shooting view (`PictureEffectPlusS1OffEEStateKeyHandler.smali`) and the live preset menu (`PictureEffectPlusOptionMenuLayout.smali`).
  - Temporarily bypasses Ricoh ISP LUT, matrix, and WB shift registers while held, letting you compare the original un-filtered viewfinder feed against the active Ricoh film preset in real time.
- **Tri-Lingual Floating Compare Badge (`PictureEffectPlusStableLayout.smali`)**:
  - Injected `attachCompareBadge()` / `detachCompareBadge()` into `StableLayout` lifecycle (`createView()` / `detachView()`), displaying a high-contrast centered translucent badge (`"ORIGINAL (BEFORE)"`, `"原片對比 (Original)"`, `"原片对比 (Original)"`) in shooting view and updating the preset title inside the live menu.
- **Fail-Safe Filter Restoration**:
  - Hooked `pushedS1Key()` (half-press shutter), `StableLayout.onPause()`, and `OptionMenuLayout.onPause()` to invoke `RicohHook.ensureFilterRestored()`, guaranteeing the active Ricoh preset is immediately re-applied if you half-press the shutter, exit the menu, or switch modes while holding C2.
- **Tier 5 Bytecode Integrity Auditor Expansion**:
  - Updated `tools/testbench/test_patched_apk.py` to audit `PictureEffectPlusStableLayout.smali` badge lifecycle hooks, `OptionMenuLayout` & `S1OffEEStateKeyHandler` C2/Delete compare handlers, `pushedS1Key()` restore guard, and `RicohHook` bypass/compare methods (**29/29 PASS**).
- **Inherited Core Capabilities**:
  - Live Viewfinder Preview Menu (`setupLivePreviewMenu`) with real-time EVF/LCD film simulation preview.
  - Fast-path HAL/DMA deduplication, split style backup flags, `Locale` caching, and `AppLog` trace silencing.
  - Full user camera state isolation & faithful restoration (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`, `DRO`, `HDR`, `LB`/`CC`).
  - Drive mode native preservation (`setSADriveMode()` no-op) & RAW mode lock elimination (`RAW + JPEG` and pure `RAW`).
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

### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v2.2.0 (B3.2) 发布

本版本重磅推出 **C2 / 删除键按住实时原片对比 (Before/After)** 功能！无论在取景拍摄界面还是实时滤镜菜单中，按住 **C2 / 删除键** 即可瞬时旁路理光滤镜，实时预览机身原片画面对比效果！

#### 🌟 核心更新与亮点
- **按住对比机身原片 (`RicohHook.setBypassPreview` / `handleShootingCompareKey` / `handleMenuCompareKey`)**:
  - 在拍摄取景界面 (`PictureEffectPlusS1OffEEStateKeyHandler.smali`) 与实时滤镜菜单 (`PictureEffectPlusOptionMenuLayout.smali`) 中全面接入 **C2 / 删除键** 按住与松开事件 (`onDeleteKeyPushed` / `onDeleteKeyReleased` / `onCustom2KeyPushed` / `onCustom2KeyReleased`)；
  - 按住时瞬时旁路理光 ISP LUT、色彩矩阵与白平衡偏移，实时在 EVF/屏幕上预览未加滤镜的机身原片画面，方便与胶片模拟效果进行直觉对比。
- **三语悬浮对比提示徽章 (`PictureEffectPlusStableLayout.smali`)**:
  - 在 `StableLayout` 生命周期 (`createView()` / `detachView()`) 中挂载 `attachCompareBadge()` / `detachCompareBadge()`，在取景画面顶部居中显示高对比半透明悬浮提示（`"原片对比 (Original)"` / `"原片對比 (Original)"` / `"ORIGINAL (BEFORE)"`），并在菜单预览时同步更新预设标题提示。
- **防呆自动恢复保护**:
  - 在 `pushedS1Key()`（半按快门对焦）、`StableLayout.onPause()` 与 `OptionMenuLayout.onPause()` 中强制调用 `RicohHook.ensureFilterRestored()`，确保半按快门、退出菜单或切换模式时瞬时恢复理光滤镜状态。
- **Tier 5 字节码审计增强**:
  - 扩充 `tools/testbench/test_patched_apk.py`，全面审计 `StableLayout` 徽章生命周期、双界面 C2/删除键事件、`pushedS1Key()` 恢复守卫及 `RicohHook` 旁路对比逻辑（**29/29 项全绿通过**）。
- **继承特性**:
  - 实时取景预览菜单 (`setupLivePreviewMenu`)，告别不透明静态样张 PNG；
  - HAL 硬件状态去重加速、独立参数备份标志、`Locale` 缓存与高频 `AppLog` 静默；
  - 机身参数状态隔离备份与无损忠实还原 (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`, `DRO`, `HDR`, `LB`/`CC`)；
  - 驱动模式原生保护 (`setSADriveMode()` 空操作) 与 RAW 模式锁定全面终结；
  - BIONZ X ISP 硬件寄存器彻底清洗与杜绝黑白锁定，兼容 PMCA 一代与二代全部微单/黑卡机型。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已通过 29 项跨机型测试台验证的正式安装包（纯 V1 签名 + 4 字节对齐）。
- `Ricoh_Camera.apk`：同上安装包副本。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="繁體中文">繁體中文</h3>

### 索尼相機理光底片濾鏡模組 (Sony PMCA Ricoh Mod) v2.2.0 (B3.2) 發布

本版本重磅推出 **C2 / 刪除鍵按住即時原片對比 (Before/After)** 功能！無論在取景拍攝介面還是即時濾鏡選單中，按住 **C2 / 刪除鍵** 即可瞬時旁路理光濾鏡，即時預覽機身原片畫面對比效果！

#### 🌟 核心更新與亮點
- **按住對比機身原片 (`RicohHook.setBypassPreview` / `handleShootingCompareKey` / `handleMenuCompareKey`)**:
  - 在拍攝取景介面 (`PictureEffectPlusS1OffEEStateKeyHandler.smali`) 與即時濾鏡選單 (`PictureEffectPlusOptionMenuLayout.smali`) 中全面接入 **C2 / 刪除鍵** 按住與放開事件 (`onDeleteKeyPushed` / `onDeleteKeyReleased` / `onCustom2KeyPushed` / `onCustom2KeyReleased`)；
  - 按住時瞬時旁路理光 ISP LUT、色彩矩陣與白平衡偏移，即時在觀景窗/螢幕上預覽未套用濾鏡的機身原片畫面，方便與底片模擬效果進行直覺對比。
- **三語懸浮對比提示徽章 (`PictureEffectPlusStableLayout.smali`)**:
  - 在 `StableLayout` 生命週期 (`createView()` / `detachView()`) 中掛載 `attachCompareBadge()` / `detachCompareBadge()`，在取景畫面頂部置中顯示高對比半透明懸浮提示（`"原片對比 (Original)"` / `"原片对比 (Original)"` / `"ORIGINAL (BEFORE)"`），並在選單預覽時同步更新預設標題提示。
- **防呆自動恢復保護**:
  - 在 `pushedS1Key()`（半按快門對焦）、`StableLayout.onPause()` 與 `OptionMenuLayout.onPause()` 中強制呼叫 `RicohHook.ensureFilterRestored()`，確保半按快門、退出選單或切換模式時瞬時恢復理光濾鏡狀態。
- **Tier 5 位元組碼審計增強**:
  - 擴充 `tools/testbench/test_patched_apk.py`，全面審計 `StableLayout` 徽章生命週期、雙介面 C2/刪除鍵事件、`pushedS1Key()` 恢復守衛及 `RicohHook` 旁路對比邏輯（**29/29 項全綠通過**）。
- **繼承特性**:
  - 即時取景預覽選單 (`setupLivePreviewMenu`)，告別不透明靜態樣張 PNG；
  - HAL 硬體狀態去重加速、獨立參數備份旗標、`Locale` 快取與高頻 `AppLog` 靜默；
  - 機身參數狀態隔離備份與無損忠實還原 (`ColorMode`, `Contrast`, `Saturation`, `Sharpness`, `DRO`, `HDR`, `LB`/`CC`)；
  - 驅動模式原生保護 (`setSADriveMode()` 空操作) 與 RAW 模式鎖定全面終結；
  - BIONZ X ISP 硬體暫存器徹底清洗與杜絕黑白鎖定，相容 PMCA 一代與二代全部微單眼/黑卡機型。

#### 📦 附件說明
- `PictureEffectPlus_Ricoh.apk`：已通過 29 項跨機型測試台驗證的正式安裝包（純 V1 簽名 + 4 位元組對齊）。
- `Ricoh_Camera.apk`：同上安裝包副本。

#### 🚀 安裝方式
```bash
./scripts/install.sh <相機IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v2.2.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B3.2) - C2/删除键按住实时原片对比 (Before/After) & 防呆自动恢复"
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
    parser.add_argument('--tag', default="v2.2.0", help="Release tag (default: v2.2.0)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
