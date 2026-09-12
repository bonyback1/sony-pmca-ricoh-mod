# Changelog

<p align="center">
  <strong>English</strong> |
  <strong><a href="CHANGELOG.zh-CN.md">简体中文</a></strong> |
  <strong><a href="CHANGELOG.zh-TW.md">繁體中文</a></strong>
</p>

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-09-12 (B2.1)

### Added & Enhanced (Runtime Adaptive Multi-Language Engine)
- **Zero-Configuration Runtime Locale Auto-Perception (`RicohHook.getLanguageType`)**:
  - Implemented dynamic runtime locale detection using Android's underlying `Locale.getDefault()`.
  - Automatically identifies whether the camera firmware is running in **English / Global (0)**, **Traditional Chinese (1, Taiwan / Hong Kong / Macau)**, or **Simplified Chinese (2, Mainland China)** with zero manual configuration.
- **Dynamic Localized Presets & Guides (`getFilterName` & `getFilterGuide`)**:
  - Dynamically switches filter names on the fly across in-camera menus, floating OSD badges, and dial scrolling:
    - **`pop-color`**: `Ricoh GR Positive Film` / `理光 GR 正片` / `理光 GR 正片`
    - **`retro-photo`**: `Ricoh Negative Film` / `理光 負片` / `理光 负片`
    - **`richtone-mono`**: `High Contrast B&W` / `高對比黑白` / `高对比黑白`
    - **`rough-mono`**: `Moriyama Daido B&W` / `森山大道風` / `森山大道风`
    - **`watercolor`**: `Cross Process` / `正負逆沖` / `正负逆冲`
  - Dynamically localizes detailed guide texts (`getMenuItemGuideText`) for all 5 presets.
- **Dynamic App Title Binding in UI**:
  - Bound shooting OSD overlay title (`AppNameView`) and option menu header (`mScreenTitle`) dynamically to `RicohHook.getAppTitle()`, showing `Ricoh Camera`, `理光相機`, or `理光相机`.
- **Tri-State `resources.arsc` Launcher Localization**:
  - Repacked global resource string pool to map camera system launcher entries:
    - Traditional Chinese: `理光相機`
    - Simplified Chinese: `理光相机`
    - English and 30+ other international camera languages: `Ricoh Camera`

## [1.2.0] - 2026-09-12 (B2.0)

### Added & Enhanced (Ricoh GR III Color Science Overhaul - Phase 1)
- **Pre-ISP Hardware White Balance Shift Injection & Safe State Restoration**:
  - Leverages Sony's private hardware white balance offset APIs within `RicohHook`: `setLightBalanceForWhiteBalance` (LB amber/blue temperature bias, range $[-14, +14]$) and `setColorCompensationForWhiteBalance` (CC green/magenta compensation, range $[-14, +14]$).
  - **Ricoh Positive Film**: Injects $LB=+2$ (amber warmth) and $CC=-1$ (subtle magenta tint), recreating the signature warm sunny base of Ricoh GR3 slide film.
  - **Ricoh Negative Film**: Injects $LB=+4$ (pronounced warm amber) and $CC=-2$ (magenta nuance), crafting a gentle yellowish vintage film base.
  - **Cross Process**: Injects $LB=-3$ (cool cyan-blue) and $CC=+2$ (emerald green), producing a dramatic cross-processed look.
  - **Monochrome Presets**: Maintains $LB=0, CC=0$ for neutral grayscale balance.
  - **User State Preservation & Zero-Residue Recovery**: Automatically snapshots user's preexisting camera WB offsets upon first activation and restores them cleanly upon switching filters or exiting, eliminating persistent color contamination.
- **1024-Point 10-bit Gamma Curves with Baked EV Compensation**:
  - Bypasses `setExposureCompensation()` to avoid interfering with physical camera dials and exposure meters; directly bakes the $2^{\Delta \text{EV}}$ sensitivity ratio into 1024-point non-linear Gamma lookup tables:
    - **Ricoh Positive Film**: Bakes -0.33 EV under-exposure to suppress blown highlights and enrich sky blue and highlight saturation.
    - **Moriyama Daido Style**: Bakes -0.33 EV under-exposure to amplify graphic black-and-white street contrast.
    - **Ricoh Negative Film**: Bakes +0.33 EV over-exposure combined with matte shadow floor lift (~35) to replicate wide negative film latitude and soft shadow tonality.
- **Split-Toning Calibrated 3×3 Color Matrices**:
  - Re-optimized and applied row-sum normalized ($\sum_j M_{ij} = 1024$) Q10 matrices, ensuring unshifted neutral grays.
  - Capitalizes on the BIONZ X ISP pipeline (*RAW Bayer $\rightarrow$ Pre-WB Shift $\rightarrow$ Demosaic $\rightarrow$ 1024-Point Non-linear Gamma $\rightarrow$ Post 3×3 Matrix*):
    - Pre-WB introduces warmth before entering non-linear S-curves, naturally decoupling shadows and highlights; post-matrix dampens excess highlight magenta and boosts foliage greens, perfectly achieving Ricoh GR3's hallmark **"Cool cyan shadows, warm amber highlights" (Split Toning)** on Sony cameras.

## [1.1.4] - 2026-09-11 (B1.4)

### Fixed & Enhanced (Architectural Hardening based on PMCA Bible)
- **Eliminated Native `DeviceBuffer` DMA Memory Leak**:
  - In `RicohHook.applyHook`, immediately invokes `GammaTable.release()` after calling `CameraEx.setExtendedGammaTable()`.
  - Added strict `try-finally` exception protection ensuring the 2KB native DMA device buffer is unconditionally released back to the Linux kernel/V4L2 hardware driver even on exceptions.
  - Fixes crash/freeze bug when repeatedly toggling menus, adjusting ISO/aperture via Fn, or reviewing photos in playback.
- **Single Atomic `setParameters` Commit (Fix Cascading Overwrite)**:
  - Eliminated secondary and tertiary IPC calls to `CreativeStyleController.setValue` and `DROAutoHDRController.setValue` that inadvertently reloaded user backup settings and overwrote the neutral 0-offsets.
  - Merged `setColorMode("standard")`, contrast 0, saturation 0, sharpness 0, `setDROMode("off")`, `setHDRMode("off")`, `setPictureEffect("off")`, and `setRGBMatrix` into a single atomic `setParameters(p1)` HAL commit.
- **Eliminated EVF / LCD Transitional Flicker During Filter Dialing**:
  - In `PictureEffectPlusController.setPlusPictureEffect`, injected smart check `RicohHook.isRicohPreset(value)`:
  - When rotating dials directly between Ricoh presets, now bypasses the intermediate `resetPictureEffectSetting` (which previously wiped tone curves and loaded identity matrices for 2ms before applying new presets).
  - Provides instantaneous, seamless filter switching with zero black/neutral screen flicker and 50% reduced Binder IPC overhead.
- **Matrix Reset Hardware Bypass**:
  - In `RicohHook.resetHook`, passes `null` to `CameraEx$ParametersModifier.setRGBMatrix(null)` instead of writing an identity matrix, allowing BIONZ X ISP to cleanly bypass hardware matrix multiplier logic and save battery power.
- **Typo Fix**:
  - Corrected guide string typo `"森山大道风粗粞高对比黑白"` to `"森山大道风粗粝高对比黑白"`.

## [1.1.3] - 2026-09-10 (B1.3)

### Fixed & Enhanced
- **Decoupled Filter Baseline from Camera Creative Style (Fix "Clear" Style Superposition)**:
  - Resolved issue where Ricoh presets inherited and superimposed with the camera's native Creative Style (e.g. "Clear", "Vivid", or user contrast offsets).
  - In `RicohHook.applyHook`, explicitly enforces `CameraEx$ParametersModifier.setColorMode("standard")`, resets contrast/saturation/sharpness offsets to 0, and synchronizes `CreativeStyleController` and `DROAutoHDRController`.
  - Guarantees 100% pure, consistent color pipeline independent of pre-existing camera menu styles.
- **Redesigned Filmic Gamma Curves for All 5 Presets (Eliminate Harsh Contrast & Crushed Shadows)**:
  - **Ricoh Positive Film**: Replaced steep sigmoid ($k=8.0$, midtone slope 2.06) with natural filmic curve (midtone slope ~1.25, toe lift to protect shadows from input 64: 14 -> 45, smooth highlight shoulder to 1020). Restores authentic Ricoh GR positive film color tone, transparent shadows, and rich dynamic range.
  - **Ricoh Negative Film**: Softened midtone contrast (slope ~1.08), preserved matte black shadow lift (35) and rolled-off highlights (985) for classic vintage film mood.
  - **Ricoh High Contrast B&W**: Adjusted contrast slope from 2.75 to 1.81, retaining punchy graphic blacks while recovering fine textures from digital black clipping.
  - **Moriyama Daido Rough B&W**: Rebalanced slope from 3.94 (binary-like thresholding) to 2.38, preserving harsh street noir look with actual edge and structure rendition.
  - **Ricoh Cross Process**: Adjusted midtone slope to 1.25 with toe lift 8, providing clean cross-processing color shifts without muddy shadows.
- **Clean Neutral Reset**:
  - `RicohHook.resetHook` safely restores standard color mode and 0-offsets when exiting or switching presets.

## [1.1.2] - 2026-09-09 (B1.2)

### Fixed & Enhanced
- **Clean Exit & Lifecycle Management (Fix Exit Loop / Re-entry Bug)**:
  - Fixed root cause where clicking "Exit application" caused the app to repeatedly restart or bounce back into the app instead of returning cleanly to native camera shooting mode or app launcher.
  - Injected resume information reset in `AppRoot.finish(FINISH_TYPE)`: sends broadcast resetting active application to `ScalarALauncher` and clearing `resume_key` and `pullingback_key`, ensuring `DAConnectionManagerService` will not resurrect `PictureEffectPlus` upon hardware/sensor state transitions.
  - Injected `Activity.finish()` in `AppRoot.finish(FINISH_TYPE)` so the Android Activity is cleanly finished and destroyed by ActivityManagerService instead of lingering in the task stack as `PAUSED`.
  - Injected `android.os.Process.killProcess(Process.myPid())` in `AppRoot.onDestroy()` for clean termination and memory reclamation.
  - Preserved power switch sleep/wake resume behavior while shooting.

## [1.1.1] - 2026-09-09 (B1.1)

### Fixed & Enhanced
- **Default Startup Filter (Ricoh GR Positive Film)**:
  - Fixed an issue where the app stayed on a later legacy filter (`part-color-plus` at index 5) due to stale camera flash storage.
  - Added preset validation in `PictureEffectPlusController.getBackupEffectValue`: non-Ricoh or legacy values automatically fallback to `pop-color` (Ricoh Positive Film) and repair flash storage.
  - Injected cold boot reset in `PictureEffectPlus.onBoot` (`BootFactor.LUNCHER`): launching the app from the camera application list now unconditionally defaults to the first filter (Ricoh Positive Film, index 0).
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
  - Default startup effect changed to `pop-color` (Ricoh Positive Film) in `PictureEffectPlusOptionMenuLayout`.
  - Added null safety guards in `getLastStoredValues` and `setPreviousMenuID` to prevent potential NPE crashes.
  - Added binary string pool patcher for `resources.arsc` to ensure "Ricoh Camera" system-wide display name consistency.
  - Added key converter and S1 key handler compatibility patches.

## [1.0.0] - 2026-09-08

### Added
- **5 Ricoh Film Presets**:
  - `pop-color` -> **Ricoh GR Positive Film**: High-contrast S-curve with signature GR saturation.
  - `retro-photo` -> **Ricoh Negative Film**: Lifted black point (matte shadows) with warm vintage highlights.
  - `richtone-mono` -> **High Contrast B&W**: BT.601 perceptual luminance weighting with steep monochrome curve.
  - `rough-mono` -> **Moriyama Daido Style**: Aggressive red-filter channel weighting with high-grain contrast.
  - `watercolor` -> **Cross Process**: Dual-tone cyan/yellow-green curve shift.
- **Hardware ISP Direct Injection**:
  - Implemented `RicohHook` smali hook interfacing directly with `com.sony.scalar.hardware.CameraEx`.
  - Zero shutter lag, EVF real-time preview, and full hardware burst shooting capability (`burstableTakePicture`).
- **Tooling & Automation**:
  - `tools/patch_apk.py`: Automated decompile, smali injection, title update, menu update, build, and sign toolchain.
  - `tools/sign_apk.py`: Android 4.1.2 Apache Harmony compatible v1 signer.
  - `tools/generate_ricoh_hook.py`: Gamma table (1024-point) & 3x3 color matrix smali generator.
  - `tools/update_menu_data.py`: Dynamic `MenuData.xml` filter descriptor patcher.
  - `scripts/install.sh`: Interactive Wi-Fi ADB installer with auto-detection and troubleshooting hints.
- **Documentation**:
  - Full reverse engineering & ISP color pipeline technical architecture documentation.
  - Sony A6300 mobile transfer & pairing guide.
