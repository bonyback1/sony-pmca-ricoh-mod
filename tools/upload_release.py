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

### Sony PMCA Ricoh Camera Mod v1.7.0 (B2.5) Released

This release introduces the **Steve McCurry Kodachrome Documentary Film Profile**, completely overhauling preset slot 5 with legendary slide film rendering, alongside our signature RAW+JPEG dual-output pipeline and universal PMCA hardware architecture!

#### 🌟 Key Highlights & Features
- **Steve McCurry Kodachrome 64/25 Documentary Film Profile (Preset Slot 5)**:
  - Replaces legacy Ricoh Cross Process with an authentic documentary film profile inspired by Magnum master photographer Steve McCurry and Kodak Kodachrome 64/25.
  - **Pure Slide Film Black Floor ($D_{\min} = 0$)**: Strips away lifted milky fog in shadows, delivering deep, punchy slide film contrast.
  - **1024-Point Non-Linear Tone Curve**: Custom Gamma curve with baked-in -0.33 EV underexposure to densify midtone and shadow gradations, combined with a 1.35 contrast slope and natural highlight roll-off.
  - **Calibrated Kodachrome 64 Hardware Color Matrix**: Decomposed asymmetric RGB matrix `[1115, -87, -4, 31, 1011, -18, 9, 62, 953]` mapped directly to camera hardware registers, yielding signature rich primary reds/yellows, golden highlights, and deep cyan skies.
  - **Pre-ISP Hardware White Balance Offset**: Embedded LB=+2 (warm amber light balance) shift, recreating Steve McCurry's hallmark "golden hour" warmth and rich skin tones celebrated in *National Geographic*.
  - **Zero Color Contamination**: Enforced `sIdentityMatrix` hardware reset upon filter switching or exit, preventing persistent color shifts.
- **Tri-Lingual Zero-Config Adaptive Engine**:
  - English: `Steve McCurry` / `Steve McCurry Kodachrome documentary film profile`
  - 繁體中文: `麥凱瑞 Kodachrome` / `馬格南大師 Steve McCurry 經典 Kodachrome 濃郁暖調紀實底片色彩`
  - 简体中文: `麦凯瑞 Kodachrome` / `马格南大师 Steve McCurry 经典 Kodachrome 浓郁暖调纪实胶片色彩`
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

### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.7.0 (B2.5) 发布

本版本重磅推出 **Steve McCurry 麦凯瑞 Kodachrome 传奇纪实胶片色彩**，彻底重塑 5 号预设位，配合 RAW+JPEG 双格式解锁与全机型硬件兼容架构，带来极致的马格南人文纪实直出体验！

#### 🌟 核心更新与亮点
- **麦凯瑞 Kodachrome 64/25 传奇纪实反转片色彩 (5号预设位重塑)**:
  - 彻底淘汰原版实用度较低的正负逆冲 (Cross Process) 滤镜，升级为致敬马格南摄影大师 Steve McCurry 与 Kodak Kodachrome 64/25 的传奇纪实色彩；
  - **极致纯净反转片黑位 ($D_{\min} = 0$)**: 彻底清除暗部雾灰发白浮层，重现反转片标志性的深邃油润纯黑与扎实反差；
  - **1024 阶非线性微曲率 Gamma 曲线**: 定制烘焙 -0.33 EV 曝光压暗以大幅增加暗部与中灰阶色彩密度，搭配 1.35 陡峭反差坡度与优雅高光滚降；
  - **精调 Kodachrome 64 硬件颜色矩阵**: 将非对称柯达色度矩阵 `[1115, -87, -4, 31, 1011, -18, 9, 62, 953]` 写入硬件寄存器，还原浓郁鲜艳的红黄原色、温暖金色高光与独特的青蓝天空；
  - **前置硬件白平衡偏置**: 注入硬件级 LB=+2 暖琥珀色温偏移，完美再现《国家地理》经典「黄金时刻」暖调氛围与极具戏剧张力的人文肤色；
  - **硬件色彩中立性防御**: 强化 `sIdentityMatrix` 硬件复位机制，确保切换滤镜或退出应用时硬件寄存器彻底归零，绝不造成机身偏色。
- **三语自适应机身菜单与指南**:
  - 英文：`Steve McCurry` / `Steve McCurry Kodachrome documentary film profile`
  - 繁体中文：`麥凱瑞 Kodachrome` / `馬格南大師 Steve McCurry 經典 Kodachrome 濃郁暖調紀實底片色彩`
  - 简体中文：`麦凯瑞 Kodachrome` / `马格南大师 Steve McCurry 经典 Kodachrome 浓郁暖调纪实胶片色彩`
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

### 索尼相機理光底片濾鏡模組 (Sony PMCA Ricoh Mod) v1.7.0 (B2.5) 發布

本版本重磅推出 **Steve McCurry 麥凱瑞 Kodachrome 傳奇紀實底片色彩**，徹底重塑 5 號預設位，配合 RAW+JPEG 雙格式解鎖與全機型硬體相容架構，帶來極致的馬格南人文紀實直出體驗！

#### 🌟 核心更新與亮點
- **麥凱瑞 Kodachrome 64/25 傳奇紀實正片色彩 (5號預設位重塑)**:
  - 徹底淘汰原版實用度較低的正負逆沖 (Cross Process) 濾鏡，升級為致敬馬格南攝影大師 Steve McCurry 與 Kodak Kodachrome 64/25 的傳奇紀實色彩；
  - **極致純淨正片黑位 ($D_{\min} = 0$)**: 徹底清除暗部霧灰泛白浮層，重現正片標誌性的深邃油潤純黑與扎實反差；
  - **1024 階非線性微曲率 Gamma 曲線**: 定制烘焙 -0.33 EV 曝光壓暗以大幅增加暗部與中階色彩密度，搭配 1.35 陡峭反差坡度與優雅高光滾降；
  - **精調 Kodachrome 64 硬體顏色矩陣**: 將非對稱柯達彩度矩陣 `[1115, -87, -4, 31, 1011, -18, 9, 62, 953]` 寫入硬體暫存器，還原濃郁鮮豔的紅黃原色、溫暖金色高光與獨特的青藍天空；
  - **前置硬體白平衡偏移**: 注入硬體級 LB=+2 暖琥珀色溫偏移，完美再現《國家地理》經典「黃金時刻」暖調氛圍與極具戲劇張力的人文膚色；
  - **硬體色彩中立性防禦**: 強化 `sIdentityMatrix` 硬體復位機制，確保切換濾鏡或退出應用程式時硬體暫存器徹底歸零，絕不造成機身色偏。
- **三語自適應機身選單與指南**:
  - 英文：`Steve McCurry` / `Steve McCurry Kodachrome documentary film profile`
  - 繁體中文：`麥凱瑞 Kodachrome` / `馬格南大師 Steve McCurry 經典 Kodachrome 濃郁暖調紀實底片色彩`
  - 簡體中文：`麦凯瑞 Kodachrome` / `马格南大师 Steve McCurry 经典 Kodachrome 浓郁暖调纪实胶片色彩`
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

def publish_release(token, tag="v1.7.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B2.5) - 麦凯瑞 Kodachrome 纪实胶片色彩与 RAW+JPEG 全格式支持"
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
    parser.add_argument('--tag', default="v1.7.0", help="Release tag (default: v1.7.0)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
