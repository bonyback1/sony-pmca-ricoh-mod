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

DEFAULT_BODY = """### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.5.0 (B2.3) 发布

本版本重磅推出 **PMCA 全机型跨代硬件兼容架构** 与 **四阶全方位自动化测试工作台**！通过底层防御性 HAL 探测、优雅降级与纯正 V1 签名 / 4 字节内存对齐，确保应用在初代与二代所有索尼 PlayMemories Camera Apps 相机上稳健运行，实现 19/19 项自动化测试 100% 全通！

#### 🌟 核心更新与调优
- **PMCA 全机型硬件防御性架构与优雅降级**:
  - 全面支持 PMCA 一代（Android 2.3.7 / API 10：A7、A7R、A6000、NEX-5R/6）与 PMCA 二代（Android 4.1.2 / API 16：A6300、A6500、A7M2、A7R2、RX100 系列）；
  - 对所有二代专有硬件 API（`setRGBMatrix([I)V`、`createGammaTable()`、`setExtendedGammaTable()`）引入防御性 `try-catch` 与非重掷回退机制，在不支持 10-bit 伽马表或色彩矩阵的老机型上平滑降级至基础 ISP 参数控制，杜绝 `NoSuchMethodError` 崩溃；
  - 深度防护脆弱 HAL 硬件寄存器（`setColorMode`、`setDROMode`、`setHDRMode`），消除机身固件拒绝导致的相机线程崩溃；
  - 严格保障 DMA 内存安全生命周期：`GammaTable.release()` 无论成功或异常分支均百分百触发，消除内核 DMA 泄漏隐患。
- **纯正 PMCA 兼容 V1 JAR 签名器与内置 4 字节 ZipAlign 引擎**:
  - 使用专用 `sign_apk.py`（基于 OpenSSL `smime -sign -noattr -binary`）生成纯净 V1 JAR 签名，杜绝 v2/v3 签名块与 CMS 签名属性导致的 `INSTALL_PARSE_FAILED_NO_CERTIFICATES`；
  - 签名引擎原生内置纯 Python 4 字节内存对齐（ZipAlign），确保 `resources.arsc` 等所有存储资源严格对齐；
  - 复用项目调试证书（`debug.keystore` -> `tools/debug.pem`），支持免卸载直接覆盖升级。
- **四阶全方位自动化测试工作台 (`tools/testbench/`)**:
  - Tier 1（Dalvik 字节码）、Tier 2（PMCA 框架符号与 HAL 安全）、Tier 3（转盘与按键人体工程学）、Tier 4（V1 签名与打包合规），**19/19 项检查全部通过 (100% PASS)**。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已通过 19 项跨机型测试台验证的正式安装包（纯 V1 签名 + 4 字节对齐）。
- `Ricoh_Camera.apk`：同上安装包副本。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.5.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B2.2) - 全机型跨代硬件兼容 (A7/A6000/A6300/RX100) 与四阶自动化测试工作台"
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
