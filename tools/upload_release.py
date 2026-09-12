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

DEFAULT_BODY = """### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.3.0 (B2.1) 发布

本版本正式引入相机运行时「自适应多语言」引擎，依托 Android 底层 Locale 自动感知，实现一套统一 APK 在 English、繁體中文（台灣/香港）、简体中文（大陆）及其他全球系统语言下的无感自适应匹配！

#### 🌟 核心更新与调优
- **运行时 Locale 自动感知引擎 (`RicohHook.getLanguageType`)**:
  - 底层调用 `Locale.getDefault()` 实时感知机身语言，零人工配置；
  - 自动归类为英文/全球通用 (0)、繁體中文 (1) 与 简体中文 (2)，当用户切换相机语言时，软件全自动无感刷新。
- **动态自适应滤镜名称与帮助指南 (`getFilterName` / `getFilterGuide`)**:
  - 滤镜槽位与浮层提示支持三态自动匹配：
    - `pop-color`：`Ricoh GR Positive Film` / `理光 GR 正片` / `理光 GR 正片`
    - `retro-photo`：`Ricoh Negative Film` / `理光 負片` / `理光 负片`
    - `richtone-mono`：`High Contrast B&W` / `高對比黑白` / `高对比黑白`
    - `rough-mono`：`Moriyama Daido B&W` / `森山大道風` / `森山大道风`
    - `watercolor`：`Cross Process` / `正負逆沖` / `正负逆冲`
- **UI 界面动态标题绑定**:
  - 取景界面顶部 OSD 标题（`AppNameView`）与选项菜单顶部标题（`mScreenTitle`）均动态绑定至 `RicohHook.getAppTitle()`，显示为 `Ricoh Camera`、`理光相機` 或 `理光相机`。
- **系统级桌面应用图标三态本地化 (`resources.arsc`)**:
  - 资源字符串池精准匹配：繁体中文系统显示「理光相機」、简体中文系统显示「理光相机」、英文及其他 30 余种语言统一显示「Ricoh Camera」。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已签名并验证通过的正式安装包（集成 Android 4.1.2 兼容的 v1/v2/v3 签名）。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.3.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
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
