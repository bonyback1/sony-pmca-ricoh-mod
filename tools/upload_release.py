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

DEFAULT_BODY = """### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.2.0 (B2.0) 发布

本版本正式落地理光 GR3 胶片色彩科学深度重构（第一阶段）：引入硬件级白平衡偏移注入与现场保护、Gamma 曲线内嵌曝光补偿烘焙，以及全新的行和归一化高低光分色 3×3 矩阵。

#### 🌟 核心更新与调优
- **硬件级白平衡偏移注入与用户现场彻底恢复 (Hardware White Balance Shifts)**:
  - 针对理光 GR3 直出色彩底层物理特性，在 `RicohHook` 中深度注入硬件级白平衡偏移调用：`setLightBalanceForWhiteBalance`（LB 琥珀/蓝色温偏置，范围 $[-14, +14]$）与 `setColorCompensationForWhiteBalance`（CC 绿色/洋红色彩补偿，范围 $[-14, +14]$）。
  - **理光 GR 正片**: 注入 $LB=+2$ (琥珀暖调), $CC=-1$ (微洋红补偿)，重现理光 GR3 正片特有的暖阳色底。
  - **理光负片**: 注入 $LB=+4$ (明显暖琥珀), $CC=-2$ (品红微调)，打造泛黄暖调的胶片底色。
  - **正负逆冲**: 注入 $LB=-3$ (冷青蓝), $CC=+2$ (显色绿调)，呈现戏剧化冷冲印风格。
  - **黑白滤镜**: 保持 $LB=0, CC=0$ 原生灰度平衡。
  - **用户原生现场保护与零残留恢复**: 首次激活滤镜时自动保存用户原先设置的相机白平衡偏移，在切换或退出应用时精准还原，杜绝机身全局色彩污染。
- **1024 阶 10-bit Gamma 曲线内嵌曝光补偿烘焙 (EV-Baking Tone Curves)**:
  - 避开调用 `setExposureCompensation()` 对机身物理曝光拨盘与测光标尺的干扰，直接将感光量比率 $2^{\Delta \text{EV}}$ 烘焙入 1024 点 10-bit 非线性 Gamma 表：
    - **理光 GR 正片**: 内嵌 -0.33 EV 曝光压暗烘焙，有效压制高光死白，增强天空蓝与高光浓郁色彩厚度。
    - **森山大道风**: 内嵌 -0.33 EV 曝光压暗烘焙，加剧强反差街头黑白张力。
    - **理光负片**: 内嵌 +0.33 EV 曝光提亮烘焙，配合哑光黑位抬升，模拟负片超大宽容度的高光滚降与通透柔和暗部。
- **全新高低光分色校准 3×3 颜色矩阵 (Split-Toning Normalized Matrices)**:
  - 重新优化并应用严格行和归一化（$\sum_j M_{ij} = 1024$）的 Q10 矩阵，灰阶无色偏。
  - 依托 BIONZ X ISP 的「RAW Bayer $\rightarrow$ 前置 WB 偏移 $\rightarrow$ Demosaic $\rightarrow$ 1024阶非线性 Gamma $\rightarrow$ 后置 3×3 色彩矩阵」管线机制：
    - 前置 WB 注入暖调，进入非线性 S 曲线后高低光自然解耦，后置矩阵对高光压制多余洋红并强化青绿饱和度，首次在索尼微单上完美重现理光 GR3 特有的**「暗部偏冷青、亮部微泛琥珀」高低光分色 (Split Toning)**。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已签名并验证通过的正式安装包（集成 Android 4.1.2 兼容的 v1/v2/v3 签名）。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.2.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B2.0) - 理光色彩科学第一阶段重构：硬件白平衡偏移、Gamma内嵌曝光补偿与高低光分色矩阵"
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
    parser.add_argument('--tag', default="v1.1.4", help="Release tag (default: v1.1.4)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
