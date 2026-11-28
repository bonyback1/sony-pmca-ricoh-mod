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

DEFAULT_BODY = """### Sony PMCA Ricoh Camera Mod v2.2.0 (B3.2) Released

This release introduces **Instant C2 / Delete Hold-to-Compare (Before/After)** across both the live shooting viewfinder and the live preset menu, allowing photographers to compare the original un-filtered scene against any active Ricoh film profile in real time!

#### 🌟 Key Highlights & Features
- **Instant Hold-to-Compare Original Scene (`RicohHook.setBypassPreview` / `handleShootingCompareKey` / `handleMenuCompareKey`)**:
  - Added press-and-hold **C2 / Delete** key handlers (`onDeleteKeyPushed` / `onDeleteKeyReleased` / `onCustom2KeyPushed` / `onCustom2KeyReleased`) to both shooting view (`PictureEffectPlusS1OffEEStateKeyHandler.smali`) and the live preset menu (`PictureEffectPlusOptionMenuLayout.smali`).
  - Temporarily bypasses Ricoh ISP LUT, matrix, and WB shift registers while held, letting you compare the original un-filtered viewfinder feed against the active Ricoh film preset in real time.
- **Tri-Lingual Floating Compare Badge (`PictureEffectPlusStableLayout.smali`)**:
  - Injected `attachCompareBadge()` / `detachCompareBadge()` into `StableLayout` lifecycle (`createView()` / `detachView()`), displaying a high-contrast centered translucent badge in shooting view and updating the preset title inside the live menu.
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
"""

def publish_release(token, tag="v2.2.0", apk_path="PictureEffectPlus_Ricoh.apk", title=None, body=None):
    if not os.path.exists(apk_path):
        raise FileNotFoundError(f"APK not found: {apk_path}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sony-PMCA-Publisher"
    }

    title = title or f"{tag} (B3.2) - Instant C2/Delete Hold-to-Compare (Before/After) & Fail-Safe Restore"
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
