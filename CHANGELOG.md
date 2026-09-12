# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-09-12 (B2.0)

### Added & Enhanced (Ricoh GR III Color Science Overhaul - Phase 1)
- **硬件级白平衡偏移注入与现场保存/恢复 (Hardware White Balance Shifts)**:
  - 针对理光 GR3 胶片色调底层物理特性，在 `RicohHook` 中深度注入硬件级白平衡偏移调用：`setLightBalanceForWhiteBalance`（LB 琥珀/蓝色温偏置，范围 $[-14, +14]$）与 `setColorCompensationForWhiteBalance`（CC 绿色/洋红色彩补偿，范围 $[-14, +14]$）。
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

## [1.1.4] - 2026-09-11 (B1.4)

### Fixed & Enhanced (Architectural Hardening based on PMCA Bible.md)
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
- **Decoupled Filter Baseline from Camera Creative Style (Fix "Clear" / 清澈 Style Superposition)**:
  - Resolved issue where Ricoh presets inherited and superimposed with the camera's native Creative Style (创意风格, e.g. "Clear" / 清澈, "Vivid", or user contrast offsets).
  - In `RicohHook.applyHook`, explicitly enforces `CameraEx$ParametersModifier.setColorMode("standard")`, resets contrast/saturation/sharpness offsets to 0, and synchronizes `CreativeStyleController` and `DROAutoHDRController`.
  - Guarantees 100% pure, consistent color pipeline independent of pre-existing camera menu styles.
- **Redesigned Filmic Gamma Curves for All 5 Presets (Eliminate Harsh Contrast & Crushed Shadows)**:
  - **理光 GR 正片 (Ricoh Positive Film)**: Replaced steep sigmoid ($k=8.0$, midtone slope 2.06) with natural filmic curve (midtone slope ~1.25, toe lift to protect shadows from input 64: 14 -> 45, smooth highlight shoulder to 1020). Restores authentic Ricoh GR positive film color tone, transparent shadows, and rich dynamic range.
  - **理光负片 (Ricoh Negative Film)**: Softened midtone contrast (slope ~1.08), preserved matte black shadow lift (35) and rolled-off highlights (985) for classic vintage film mood.
  - **高对比黑白 (Ricoh High Contrast B&W)**: Adjusted contrast slope from 2.75 to 1.81, retaining punchy graphic blacks while recovering fine asphalt/dark textures from digital black clipping.
  - **森山大道风 (Moriyama Daido Rough B&W)**: Rebalanced slope from 3.94 (binary-like thresholding) to 2.38, preserving harsh street noir look with actual edge and structure rendition.
  - **正负逆冲 (Ricoh Cross Process)**: Adjusted midtone slope to 1.25 with toe lift 8, providing clean cross-processing color shifts without muddy shadows.
- **Clean Neutral Reset**:
  - `RicohHook.resetHook` safely restores standard color mode and 0-offsets when exiting or switching presets.

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
