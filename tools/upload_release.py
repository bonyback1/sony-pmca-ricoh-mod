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

### Sony PMCA Ricoh Camera Mod v1.9.0 (B2.7) Released

This release delivers **BIONZ X ISP Hardware State Sanitization & Complete B&W Lock Elimination**, brand-new **Pixel-Perfect Native UI & Custom Icon Assets**, **Playback Resume State Protection**, and **Streamlined Preset Menus**, backed by an upgraded 20/20 testbench suite!

#### 🌟 Key Highlights & Features
- **BIONZ X ISP Hardware State Sanitization & Zero B&W Lock**:
  - Permanently resolved the persistent monochrome lock hazard in Sony's BIONZ X ISP when switching filters or exiting the app.
  - Explicitly restored the 3×3 Identity Matrix (`sIdentityMatrix`: `[1024, 0, 0, 0, 1024, 0, 0, 0, 1024]`) instead of null on `resetHook`.
  - Cleared Partial Color extraction registers via `setColorSelectMode("off", sEmptyIntArray)` in both `applyHook` and `resetHook`.
  - Guaranteed full hardware teardown on application exit by forcing `sIsRicohActive = true` in `onTerminateHook`.
  - Upgraded automated PMCA testbench to **20/20 checks PASS (100%)** with new Tier 2 Check 5 (`check_isp_bw_lock_prevention`).
- **Redesigned Native UI & Custom Icon Assets (`src/icons/`, `tools/gen_ui_assets.py`)**:
  - Replaced legacy Sony Picture Effect icons with custom pixel-perfect dial icons (70×60) calibrated against Sony's 4-bit quantised typography.
  - Added 280×480 live preview sample images rendered directly through actual 1024-step Gamma curves and RGB matrices.
  - Streamlined `MenuData.xml`: retained strictly the 5 signature presets in `ApplicationTop`, eliminating redundant/unsupported legacy presets.
  - Patched `PictureEffectPlusPageMenuLayout.smali` to route `ApplicationSettings` cleanly to `ApplicationTop` for Ricoh presets.
- **Playback Resume & TimerTask Stability**:
  - Patched `PictureEffectPlusExecutorCreator.smali` (`forceEffectSetting()`) to immediately restore active Ricoh LUT & matrix upon returning from camera Playback mode.
  - Patched `PictureEffectPlusForceSettingState.smali` to bypass native Sony PictureEffect timer task loops for Ricoh presets.
- **Resilient ADB Wi-Fi Installation Relay (`scripts/install.sh`)**:
  - Added automated fallback to local TCP port forwarding relay (`127.0.0.1:15555 -> ${CAMERA_IP}:5555`) to circumvent macOS Local Network privacy permission blocks on direct ADB connections.
- **Inherited Core Capabilities**:
  - Drive mode & continuous burst shooting full unlock across all 5 film presets.
  - Authentic Leica Steve McCurry Documentary profile (`Leica_SteveMcCurry.cube` mathematical decomposition).
  - Full RAW + JPEG and pure RAW capture modes unlocked.
  - Authentic Ricoh GR III 3D LUT decomposition (Positive Film, Negative Film, High Contrast B&W).
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

### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.9.0 (B2.7) 发布

本版本重磅推出 **BIONZ X ISP 硬件状态彻底清洗与黑白锁定根治方案**、全新**原生定制高精拨轮图标与预览样张**、**相册回放返回状态保护**与**极简纯净菜单架构**，并全面扩充四阶跨机型自动化测试台至 20/20 全绿通过！

#### 🌟 核心更新与亮点
- **BIONZ X ISP 硬件状态彻底清洗 & 杜绝黑白滤镜锁定**:
  - 彻底攻克索尼 BIONZ X ISP 在切换滤镜或退出应用时残留分色滤镜寄存器导致其他功能误锁定黑白的硬件顽疾；
  - `resetHook` 与 `applyHook` 中显式清空分色抽取寄存器 (`setColorSelectMode("off", sEmptyIntArray)`)；
  - `resetHook` 改为显式恢复标准 3×3 单位矩阵 (`sIdentityMatrix`: `[1024, 0, 0, 0, 1024, 0, 0, 0, 1024]`)，杜绝 null 传递可能引发的硬件状态漂移；
  - 在 `onTerminateHook` 中强制置位 `sIsRicohActive = true`，确保退出 App 时硬件状态 100% 彻底复位与注销；
  - 自动化 PMCA 测试套件新增 Tier 2 Check 5 (`check_isp_bw_lock_prevention`)，测试用例扩充至 **20/20 项全绿通过 (100%)**。
- **重构原生 UI 资产与定制拨轮图标 (`src/icons/`, `tools/gen_ui_assets.py`)**:
  - 彻底替换原生照片效果过时图标，制作并注入符合索尼 4-bit 量化排版规范的定制高精拨轮图标 (70×60)；
  - 注入 280×480 原生实时取景预览样张，样张经真实 1024 阶 Gamma 曲线与 RGB 硬件矩阵精确渲染；
  - 精简优化 `MenuData.xml`：顶层 `ApplicationTop` 纯净收敛至 5 款经典签名预设，剔除所有冗余无用选项；
  - 修补 `PictureEffectPlusPageMenuLayout.smali`，理光预设点击 `ApplicationSettings` 干净重定向回 `ApplicationTop`。
- **回放返回与定时器任务稳定性增强**:
  - 修补 `PictureEffectPlusExecutorCreator.smali` (`forceEffectSetting()`)，从相册回放返回拍摄时瞬时恢复当前激活的理光 LUT 与颜色矩阵；
  - 修补 `PictureEffectPlusForceSettingState.smali`，绕过官方照片效果针对理光预设的定时器循环检查任务，避免不必要的轮询与闪烁。
- **弹性 ADB Wi-Fi 安装中继 (`scripts/install.sh`)**:
  - 内置基于 Python 的本地 TCP 端口转发中继 (`127.0.0.1:15555 -> ${CAMERA_IP}:5555`)，完美绕过 macOS 本地网络隐私权限对直连 ADB 的阻断拦截。
- **继承特性**:
  - 全套 5 款理光胶片预设全线支持高速连拍 (Hi/Mid/Lo)、速度优先连拍、定时自拍与阶段曝光；
  - 官方真·徕卡麦凯瑞纪实色彩 (`Leica_SteveMcCurry.cube` 逆向数学分解)；
  - 保持 RAW+JPEG 与纯 RAW 双格式保存能力；
  - 保持真·理光 GR3 3D LUT 正片、负片、高对比黑白逆向色彩；
  - 兼容 PMCA 一代与二代全部微单/黑卡机型，四阶测试台 20/20 项 100% 全通。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已通过 20 项跨机型测试台验证的正式安装包（纯 V1 签名 + 4 字节对齐）。
- `Ricoh_Camera.apk`：同上安装包副本。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="繁體中文">繁體中文</h3>

### 索尼相機理光底片濾鏡模組 (Sony PMCA Ricoh Mod) v1.9.0 (B2.7) 發布

本版本重磅推出 **BIONZ X ISP 硬體狀態徹底清洗與黑白鎖定根治方案**、全新**原生定制高精撥輪圖示與預覽樣張**、**相簿回放返回狀態保護**與**極簡純淨選單架構**，並全面擴充四階跨機型自動化測試台至 20/20 全綠通過！

#### 🌟 核心更新與亮點
- **BIONZ X ISP 硬體狀態徹底清洗 & 杜絕黑白濾鏡鎖定**:
  - 徹底攻克索尼 BIONZ X ISP 在切換濾鏡或退出應用程式時殘留分色濾鏡暫存器導致其他功能誤鎖定黑白的硬體頑疾；
  - `resetHook` 與 `applyHook` 中顯式清空分色抽取暫存器 (`setColorSelectMode("off", sEmptyIntArray)`)；
  - `resetHook` 改為顯式恢復標準 3×3 單位矩陣 (`sIdentityMatrix`: `[1024, 0, 0, 0, 1024, 0, 0, 0, 1024]`)，杜絕 null 傳遞可能引發的硬體狀態漂移；
  - 在 `onTerminateHook` 中強制置位 `sIsRicohActive = true`，確保退出 App 時硬體狀態 100% 徹底復位與註銷；
  - 自動化 PMCA 測試套件新增 Tier 2 Check 5 (`check_isp_bw_lock_prevention`)，測試案例擴充至 **20/20 項全綠通過 (100%)**。
- **重構原生 UI 資產與定制撥輪圖示 (`src/icons/`, `tools/gen_ui_assets.py`)**:
  - 徹底替換原生相片效果過時圖示，製作並注入符合索尼 4-bit 量化排版規範的定制高精撥輪圖示 (70×60)；
  - 注入 280×480 原生即時取景預覽樣張，樣張經真實 1024 階 Gamma 曲線與 RGB 硬體矩陣精確渲染；
  - 精簡優化 `MenuData.xml`：頂層 `ApplicationTop` 純淨收斂至 5 款經典簽名預設，剔除所有冗餘無用選項；
  - 修補 `PictureEffectPlusPageMenuLayout.smali`，理光預設點擊 `ApplicationSettings` 乾淨重定向回 `ApplicationTop`。
- **回放返回與計時器任務穩定性增強**:
  - 修補 `PictureEffectPlusExecutorCreator.smali` (`forceEffectSetting()`)，從相簿回放返回拍攝時瞬時恢復當前啟用的理光 LUT 與顏色矩陣；
  - 修補 `PictureEffectPlusForceSettingState.smali`，繞過官方相片效果針對理光預設的計時器循環檢查任務，避免不必要的輪詢與閃爍。
- **彈性 ADB Wi-Fi 安裝中繼 (`scripts/install.sh`)**:
  - 內建基於 Python 的本機 TCP 連接埠轉發中繼 (`127.0.0.1:15555 -> ${CAMERA_IP}:5555`)，完美繞過 macOS 本機網路隱私權限對直連 ADB 的阻斷攔截。
- **繼承特性**:
  - 全套 5 款理光底片預設全線支援高速連拍 (Hi/Mid/Lo)、速度優先連拍、定時自拍與包圍曝光；
  - 官方真·徠卡麥凱瑞紀實色彩 (`Leica_SteveMcCurry.cube` 逆向數學分解)；
  - 保持 RAW+JPEG 與純 RAW 雙格式儲存能力；
  - 保持真·理光 GR3 3D LUT 正片、負片、高對比黑白逆向色彩；
  - 相容 PMCA 一代與二代全部微單眼/黑卡機型，四階測試台 20/20 項 100% 全通。

#### 📦 附件說明
- `PictureEffectPlus_Ricoh.apk`：已通過 20 項跨機型測試台驗證的正式安裝包（純 V1 簽名 + 4 位元組對齊）。
- `Ricoh_Camera.apk`：同上安裝包副本。

#### 🚀 安裝方式
```bash
./scripts/install.sh <相機IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.9.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B2.7) - BIONZ X ISP 硬件状态清洗/杜绝黑白锁定与原生定制 UI 图标"
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
    parser.add_argument('--tag', default="v1.9.0", help="Release tag (default: v1.9.0)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
