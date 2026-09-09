# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-09-09 (B1.2)

### Fixed & Enhanced
- **Clean Exit & Lifecycle Management (Fix Exit Loop / Re-entry Bug)**:
  - Fixed root cause where clicking "退出应用程序" (Exit application) caused the app to repeatedly restart or bounce back into the app instead of returning cleanly to native camera shooting mode or app launcher.
  - Injected resume information reset in `AppRoot.finish(FINISH_TYPE)`: sends broadcast resetting active application to `ScalarALauncher` and clearing `resume_key` and `pullingback_key`, ensuring `DAConnectionManagerService` will not resurrect `PictureEffectPlus` upon hardware/sensor state transitions.
  - Injected `Activity.finish()` in `AppRoot.finish(FINISH_TYPE)` so the Android Activity is cleanly finished and destroyed by ActivityManagerService instead of lingering in the task stack as `PAUSED`.
  - Injected `android.os.Process.killProcess(Process.myPid())` in `AppRoot.onDestroy()` for clean termination and memory reclamation.
  - Preserved power switch sleep/wake resume behavior while shooting (powering off and on while shooting still stays in the app).

## [1.1.1] - 2026-09-09 (B1.1)

### Fixed & Enhanced
- **Default Startup Filter (理光 GR 正片)**:
  - Fixed an issue where the app stayed on a later legacy filter (`part-color-plus` at index 5) due to stale camera flash storage.
  - Added preset validation in `PictureEffectPlusController.getBackupEffectValue`: non-Ricoh or legacy values automatically fallback to `pop-color` (理光 GR 正片) and repair flash storage.
  - Injected cold boot reset in `PictureEffectPlus.onBoot` (`BootFactor.LUNCHER`): launching the app from the camera application list now unconditionally defaults to the first filter (理光 GR 正片, index 0).
  - Preserved active shooting filters across camera sleep/power cycling (`BootFactor.POWERON` / `BootFactor.APO`).
- **Key & Navigation Compatibility**:
  - Center button keycode `0xe8` bypasses custom key mapping interception to ensure reliable menu triggering and filter selection.
  - Directional keys (Left/Right) and sub-dial turns mapped to Up/Down for swift filter switching.
- **Build & Packaging**:
  - Integrated `uber-apk-signer` for dual v1/v2/v3 signing compatible with Android 4.1.2.

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
