# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-08

### Added & Improved
- **Menu Reordering & Direct Apply**:
  - Reordered `ApplicationTop` so the 5 Ricoh presets appear at positions 1-5 for instant access.
  - Enforced `ExecType="SET_VALUE"` to apply filters immediately without redundant submenus.
- **Dynamic Text & Guide Hooks**:
  - Implemented `getFilterName` and `getFilterGuide` hooks in `RicohHook` and `BaseMenuService` for dynamic in-camera title and guide text.
- **UI & Layout Enhancements**:
  - Default startup effect changed to `pop-color` (理光 GR 正片) in `PictureEffectPlusOptionMenuLayout`.
  - Added null safety guards in `getLastStoredValues` and `setPreviousMenuID` to prevent potential NPE crashes.
  - Added binary string pool patcher for `resources.arsc` to ensure "理光相机" system-wide display name consistency.
  - Added key converter and S1 key handler compatibility patches.

## [1.0.0] - 2026-09-08

### Added
- **5 Ricoh Film Presets**:
  - `pop-color` -> **理光 GR 正片 (Ricoh Positive Film)**: High-contrast S-curve with signature GR saturation.
  - `retro-photo` -> **理光负片 (Ricoh Negative Film)**: Lifted black point (matte shadows) with warm vintage highlights.
  - `richtone-mono` -> **高对比黑白 (High Contrast B&W)**: BT.601 perceptual luminance weighting with steep monochrome curve.
  - `rough-mono` -> **森山大道风 (Moriyama Daido Style)**: Aggressive red-filter channel weighting with high-grain contrast.
  - `watercolor` -> **正负逆冲 (Cross Process)**: Dual-tone cyan/yellow-green curve shift.
- **Hardware ISP Direct Injection**:
  - Implemented `RicohHook` smali hook interfacing directly with `com.sony.scalar.hardware.CameraEx`.
  - Zero shutter lag, EVF real-time preview, and full hardware burst shooting capability (`burstableTakePicture`).
- **Tooling & Automation**:
  - `tools/patch_apk.py`: Automated decompile, smali injection, title update, menu update, build, and sign toolchain.
  - `tools/sign_apk.py`: Android 4.1.2 Apache Harmony compatible v1 signer (bypasses modern CMS attribute parsing bugs).
  - `tools/generate_ricoh_hook.py`: Gamma table (1024-point) & 3x3 color matrix smali generator.
  - `tools/update_menu_data.py`: Dynamic `MenuData.xml` filter descriptor patcher.
  - `scripts/install.sh`: Interactive Wi-Fi ADB installer with auto-detection and troubleshooting hints.
- **Documentation**:
  - Full reverse engineering & ISP color pipeline technical architecture documentation.
  - Sony A6300 mobile transfer & pairing guide.
