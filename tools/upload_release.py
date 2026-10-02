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

### Sony PMCA Ricoh Camera Mod v1.8.0 (B2.6) Released

This release introduces **Continuous Burst Shooting & Full Drive Mode Unlock** across all film simulation presets, alongside the **Authentic Leica Steve McCurry Documentary Profile** mathematically decomposed directly from genuine Leica 3D LUT science!

#### 🌟 Key Highlights & Features
- **Drive Mode & Continuous Burst Shooting Full Unlock**:
  - Eliminated Sony's artificial restrictions in Picture Effect+ that prevented continuous shooting and burst drive modes on specific presets.
  - Removed `watercolor` and `richtone-mono` from the restrictive `ITEM_ID_SA_USE_EFFECT` exclusion list.
  - Hooked `PictureEffectPlusDriveModeController.smali` (`isAvailable(Ljava/lang/String;)Z`), unlocking all drive modes (Continuous Hi/Mid/Lo, Speed Priority Continuous, Self-timer, Bracket) across **all 5 film presets**.
- **Authentic Leica Steve McCurry Documentary Profile (Preset Slot 5 Upgrade)**:
  - Decomposed tone curve and color matrix mathematically directly from genuine `Leica_SteveMcCurry.cube`.
  - **Calibrated Leica Color Matrix**: Implemented hardware 3×3 RGB matrix `[1118, -62, -32, -23, 1070, -23, -45, -29, 1098]` capturing the iconic warm golden Leica color science ("德味暖金"), vibrant primaries, and natural skin tones with neutral pre-ISP LB=0 balance.
  - **1024-Point Gamma Curve**: 10-bit non-linear tone curve with pure slide film black level ($D_{\min} = 0$), dense shadow gradations, and a 1.35 contrast slope.
  - **Tri-Lingual Localization**: Updated dial titles, OSD labels, and guide descriptions:
    - English: `Leica McCurry` / `Authentic Leica Steve McCurry warm documentary profile`
    - Traditional Chinese: `徠卡麥凱瑞` / `徠卡官方 Steve McCurry 經典暖金德味紀實色彩`
    - Simplified Chinese: `徕卡麦凯瑞` / `徕卡官方 Steve McCurry 经典暖金德味纪实色彩`
- **Inherited Core Capabilities**:
  - Full RAW + JPEG and pure RAW capture modes unlocked.
  - Authentic Ricoh GR III 3D LUT decomposition (Positive Film, Negative Film, High Contrast B&W).
  - Universal PMCA cross-generation compatibility (A7, A6000, A6300, A6500, A7M2, A7R2, RX100 series).
  - 100% pass rate (19/19 checks) on the automated 4-tier PMCA verification testbench.

#### 📦 Attachments
- `PictureEffectPlus_Ricoh.apk`: Production signed release APK (Pure V1 JAR signature + 4-byte ZipAlign).
- `Ricoh_Camera.apk`: Exact mirror of the production APK.

#### 🚀 Installation
```bash
./scripts/install.sh <CAMERA_IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="简体中文">简体中文</h3>

### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.8.0 (B2.6) 发布

本版本重磅推出 **驱动模式高速连拍全面解锁** 与 **官方真·徕卡麦凯瑞纪实色彩**，突破官方对连拍的底层限制，配合 RAW+JPEG 双格式解锁与全机型硬件兼容架构，带来极致的德味与人文纪实拍摄体验！

#### 🌟 核心更新与亮点
- **驱动模式与高速连拍全线解锁 (突破官方连拍限制)**:
  - 彻底打破官方照片效果应用在复杂滤镜（水彩/原5号位、丰富色调黑白/3号位）下锁定单张拍摄的底层代码枷锁；
  - 在 `PictureEffectPlusController.smali` 中剔除 `ITEM_ID_SA_USE_EFFECT` 禁用名单（移除 `watercolor` 与 `richtone-mono`）；
  - 在 `PictureEffectPlusDriveModeController.smali` 中注入 `RicohHook.isRicohPreset()` 判断逻辑，实现**全套 5 款理光胶片预设全线支持高速连拍 (Hi/Mid/Lo)、速度优先连拍、定时自拍与阶段曝光**。
- **真·徕卡麦凯瑞纪实色彩 (Leica Steve McCurry) 重磅升级 (5号预设位)**:
  - 直接从官方母版 `Leica_SteveMcCurry.cube` 逆向数学分解，赋予 5 号位纯正徕卡影调；
  - **精调徕卡 3×3 硬件颜色矩阵**: 注入原生硬件颜色矩阵 `[1118, -62, -32, -23, 1070, -23, -45, -29, 1098]`，再现经典徕卡「德味暖金」色调与马格南大师 Steve McCurry 标志性纪实氛围，无需人工 WB 偏置 (LB=0) 即可呈现自然纯正的人文肤色与色彩厚重感；
  - **1024 阶非线性反转片 Gamma 曲线**: 纯正反转片深黑底色 ($D_{\min}=0$)，搭配 1.35 陡峭反差坡度，暗部扎实油润，高光滚降过渡自然；
  - **三语自适应机身菜单与指南**:
    - 英文：`Leica McCurry` / `Authentic Leica Steve McCurry warm documentary profile`
    - 繁体中文：`徠卡麥凱瑞` / `徠卡官方 Steve McCurry 經典暖金德味紀實色彩`
    - 简体中文：`徕卡麦凯瑞` / `徕卡官方 Steve McCurry 经典暖金德味纪实色彩`
- **继承特性**:
  - 保持 RAW+JPEG 与纯 RAW 双格式保存能力；
  - 保持真·理光 GR3 3D LUT 正片、负片、高对比黑白逆向色彩；
  - 兼容 PMCA 一代与二代全部微单/黑卡机型，四阶测试台 19/19 项 100% 全通。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已通过 19 项跨机型测试台验证的正式安装包（纯 V1 签名 + 4 字节对齐）。
- `Ricoh_Camera.apk`：同上安装包副本。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```

---

<h3 id="繁體中文">繁體中文</h3>

### 索尼相機理光底片濾鏡模組 (Sony PMCA Ricoh Mod) v1.8.0 (B2.6) 發布

本版本重磅推出 **驅動模式高速連拍全面解鎖** 與 **官方真·徠卡麥凱瑞紀實色彩**，突破官方對連拍的底層限制，配合 RAW+JPEG 雙格式解鎖與全機型硬體相容架構，帶來極致的德味與人文紀實拍攝體驗！

#### 🌟 核心更新與亮點
- **驅動模式與高速連拍全線解鎖 (突破官方連拍限制)**:
  - 徹底打破官方相片效果應用程式在複雜濾鏡（水彩/原5號位、豐富色調黑白/3號位）下鎖定單張拍攝的底層程式碼限制；
  - 在 `PictureEffectPlusController.smali` 中剔除 `ITEM_ID_SA_USE_EFFECT` 禁用名單（移除 `watercolor` 與 `richtone-mono`）；
  - 在 `PictureEffectPlusDriveModeController.smali` 中注入 `RicohHook.isRicohPreset()` 判斷邏輯，實現**全套 5 款理光底片預設全線支援高速連拍 (Hi/Mid/Lo)、速度優先連拍、定時自拍與包圍曝光**。
- **真·徠卡麥凱瑞紀實色彩 (Leica Steve McCurry) 重磅升級 (5號預設位)**:
  - 直接從官方母版 `Leica_SteveMcCurry.cube` 逆向數學分解，賦予 5 號位純正徠卡影調；
  - **精調徠卡 3×3 硬體顏色矩陣**: 注入原生硬體顏色矩陣 `[1118, -62, -32, -23, 1070, -23, -45, -29, 1098]`，再現經典徠卡「德味暖金」色調與馬格南大師 Steve McCurry 標誌性紀實氛圍，無需人工 WB 偏移 (LB=0) 即可呈現自然純正的人文膚色與色彩厚重感；
  - **1024 階非線性正片 Gamma 曲線**: 純正正片深黑底色 ($D_{\min}=0$)，搭配 1.35 陡峭反差坡度，暗部扎實油潤，高光滾降過渡自然；
  - **三語自適應機身選單與指南**:
    - 英文：`Leica McCurry` / `Authentic Leica Steve McCurry warm documentary profile`
    - 繁體中文：`徠卡麥凱瑞` / `徠卡官方 Steve McCurry 經典暖金德味紀實色彩`
    - 簡體中文：`徕卡麦凯瑞` / `徕卡官方 Steve McCurry 经典暖金德味纪实色彩`
- **繼承特性**:
  - 保持 RAW+JPEG 與純 RAW 雙格式儲存能力；
  - 保持真·理光 GR3 3D LUT 正片、負片、高對比黑白逆向色彩；
  - 相容 PMCA 一代與二代全部微單眼/黑卡機型，四階測試台 19/19 項 100% 全通。

#### 📦 附件說明
- `PictureEffectPlus_Ricoh.apk`：已通過 19 項跨機型測試台驗證的正式安裝包（純 V1 簽名 + 4 位元組對齊）。
- `Ricoh_Camera.apk`：同上安裝包副本。

#### 🚀 安裝方式
```bash
./scripts/install.sh <相機IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.8.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B2.6) - 徕卡麦凯瑞 (Leica Steve McCurry) 与全滤镜高速连拍/驱动模式全面解锁"
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
    parser.add_argument('--tag', default="v1.8.0", help="Release tag (default: v1.8.0)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
