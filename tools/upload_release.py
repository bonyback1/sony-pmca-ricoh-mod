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

DEFAULT_BODY = """### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.1.4 (B1.4) 发布

本版本深度对照索尼官方 PMCA 架构开发圣经（Bible.md）全栈规范，修复了底层 Native 硬件内存泄漏与参数级联覆盖等系统级隐患，并消除了转动拨轮切换滤镜时的取景器黑闪与迟滞。

#### 🌟 核心更新与调优
- **彻底杜绝 Native DeviceBuffer DMA 硬件内存泄漏**：
  - 依据规范，`CameraEx$GammaTable` 是底层通过 `/dev/video*` 直接分配的 Linux 内核物理 DMA 内存。此前写入 HAL 后缺失显式 `release()`，且在每次关闭菜单、按 Fn 调 ISO 或按回放查看照片返回取景器时均被触发，高频操作会耗尽缓冲池。
  - 在 `RicohHook.applyHook` 中加入严格的 `try-finally` 硬件保护，向 HAL 提交后立即释放 `table.release()`，确保整机全天候拍摄绝不死机或冻结取景器。
- **重构为单次原子参数提交（杜绝机身历史设置冲掉 0 偏移）**：
  - 彻底剔除跨单例调用 `CreativeStyleController.setValue` 与 `DROAutoHDRController.setValue` 引发的级联 IPC；
  - 直接在单一 `ParametersModifier` 中一步到位设置中性标准风格、0 对比度/饱和度/锐度、DRO/HDR 禁用、色彩矩阵与特效关闭，并执行单次原子提交。
- **拨轮切换滤镜消除取景器闪黑与 IPC 减负**：
  - 在 `setPlusPictureEffect` 入口处注入智能分发：在 5 款理光胶片预设之间转动拨轮切换时，跳过清空曲线与单位阵的中间过渡步骤，直接原子覆盖目标色彩，彻底消除 EVF/LCD 画面黑闪跳色，切换响应更迅捷。
- **色彩矩阵重置硬件旁路（降低发热与功耗）**：
  - 在 `resetHook` 中，将重置写入对角 1024 阵改为向 HAL 传入 `null`，让 BIONZ X 处理器直接 bypass 矩阵乘法器硬件，更省电。
- **字面量修正**：
  - 修正森山大道风引导词中的汉字笔误（“森山大道风粗粝高对比黑白”）。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已签名并验证通过的正式安装包（集成 Android 4.1.2 兼容的 v1/v2/v3 签名）。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.1.4", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B1.4) - 基于PMCA开发圣经的架构加固与内存防崩"
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
