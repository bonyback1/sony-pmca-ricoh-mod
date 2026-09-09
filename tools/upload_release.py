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

DEFAULT_BODY = """### 索尼相机理光胶片滤镜模组 (Sony PMCA Ricoh Mod) v1.1.2 (B1.2) 发布

本版本彻底修复了退出应用程序时反复重新唤醒进入应用的死循环 Bug，并规范了 PMCA 与 Android Activity 混合生命周期。已在索尼 ILCE-6300 真机上测试通过。

#### 🌟 核心更新与修复
- **彻底修复退出应用反复重新唤醒 Bug (Exit Loop Fix)**：
  - 深度分析索尼私有 `DAConnectionManagerService` 与 JNI 唤醒机制：此前退出时由于未清空 `resume_key` 与 `pullingback_key`，系统在切换到原生拍摄（diadem）或检测到硬件按键时，会根据 `/data/resume_info.txt` 中残留的包名信息强制重新拉起 `PictureEffectPlus`。
  - 在 `AppRoot.finish(FINISH_TYPE)` 中注入状态复位广播：退出时先向系统发送 `AppInfoReceive`，将当前激活应用显式复位为系统桌面 `ScalarALauncher` 并清空唤醒按键数组，彻底消除系统的重唤醒来源。
  - 修复 `AppRoot.finish` 未调用 `Activity.finish()` 的缺陷：在调用 `dacm.finish()` 的同时显式调用 `super.finish()`，确保 Activity 真正从 ActivityManager 任务栈中出栈并销毁，避免以 `PAUSED` 状态悬挂在后台。
  - 在 `AppRoot.onDestroy()` 中加入进程安全回收机制，确保退出后内存与相机 HAL 资源完全释放。
  - 完美保留正常拍摄时的关机/开机休眠唤醒特性（关机再开机依旧停留在当前滤镜）。
- **默认首选滤镜 (理光 GR 正片)**：
  - 启动应用 100% 默认定位在第 1 项「理光 GR 正片」。
- **按键快速切换与全系统名称统一**：
  - 中央确认键（扫描码 `0xe8`）直通滤镜选择，拨轮与方向键均可顺畅切换滤镜。
  - 54 处系统语言资源与界面标题统一显示为「理光相机」。

#### 📦 附件说明
- `PictureEffectPlus_Ricoh.apk`：已签名并验证通过的正式安装包（集成 Android 4.1.2 兼容的 v1/v2/v3 签名）。

#### 🚀 安装方式
```bash
./scripts/install.sh <相机IP> PictureEffectPlus_Ricoh.apk
```
"""

def publish_release(token, tag="v1.1.2", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
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
    parser.add_argument('--tag', default="v1.1.1", help="Release tag (default: v1.1.1)")
    parser.add_argument('--apk', default="PictureEffectPlus_Ricoh.apk", help="Path to APK binary")
    args = parser.parse_args()

    if not args.token:
        print("Error: GitHub Token is required.")
        print("Provide via --token <TOKEN> or set GITHUB_TOKEN environment variable.")
        sys.exit(1)

    publish_release(args.token, tag=args.tag, apk_path=args.apk)

if __name__ == '__main__':
    main()
