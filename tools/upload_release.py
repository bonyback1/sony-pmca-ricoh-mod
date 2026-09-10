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

DEFAULT_BODY = """### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.1.3 (B1.3) 发布

本版本重点解决了滤镜色彩与相机原有“清澈 (Clear)”等创意风格叠加的问题，并全面重构了 5 款定制滤镜的 Gamma 动力学曲线，还原纯正自然的真实理光相机胶片质感。

#### 🌟 核心更新与调优
- **彻底阻断与相机原有创意风格叠加（基准锁定）**：
  - 此前索尼官方仅在“分色+”效果下重置创意风格，切换为定制滤镜并关闭照片效果后，底层的硬件 ISP 仍会继承相机原先开启的“清澈 (Clear)”或鲜明模式及用户对比度偏移，导致对比度异常过高。
  - 在 `RicohHook.applyHook` 中强制向底层写入 `setColorMode("standard")`，对比度、饱和度、锐度偏移全部归零，并同步复位 `CreativeStyleController` 与 `DROAutoHDRController`，确保滤镜无论在何种相机设置下都拥有 100% 独立中性的纯正基准。
- **全新重构 5 款经典滤镜的 10-bit Filmic Gamma 曲线**：
  - **理光 GR 正片 (Ricoh Positive Film)**：中灰斜率从暴力的 2.06 回调至自然的 1.22~1.25，暗部抬升保护阴影细节（输入 64 映射值由 14 提升至 45），高光加入柔和滚降，彻底消除死黑，呈现真实理光正片经典的青蓝色天空、浓郁黄绿与丰富暗部层次。
  - **理光负片 (Ricoh Negative Film)**：反差斜率优化至 1.08~1.12，黑位轻度抬升至 35，呈现柔和低对比、哑光泛暖的复古胶片韵味。
  - **高对比黑白 (Ricoh High Contrast B&W)**：斜率优化至 1.81，保全深邃油墨质感的同时恢复暗部细节与胶片颗粒层次。
  - **森山大道风 (Moriyama Daido Rough B&W)**：斜率由近乎二值化的 3.94 调整至 2.38，街头黑白张力十足且保留轮廓与暗部细节。
  - **正负逆冲 (Ricoh Cross Process)**：斜率调优至 1.25，青绿暗部与暖黄高光平衡过渡，鲜明通透。
- **全生命周期与稳定性保障**：
  - 滤镜退出/切换时自动安全复位标准基准与零偏移。
  - 继承 v1.1.2 干净退出的防重入机制，以及关机开机正常停留机制。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已签名并验证通过的正式安装包（集成 Android 4.1.2 兼容的 v1/v2/v3 签名）。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.1.3", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B1.2) - 退出死循环彻底修复与生命周期规范化"
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
    parser.add_argument('--tag', default="v1.1.3", help="Release tag (default: v1.1.3)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
