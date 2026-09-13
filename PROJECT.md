# Project: Universal Sony PMCA Ricoh Camera Mod

## Architecture
- **Application**: `com.sony.imaging.app.pictureeffectplus` (Sony Picture Effect+ modded for Ricoh camera color simulation).
- **Core Technology**: Pure Dalvik Smali reverse engineering, automated byte-patching (`tools/patch_apk.py`), procedural ISP smali generation (`tools/generate_ricoh_hook.py`), and OpenSSL/Java V1 JAR signing.
- **Hardware Abstraction Layer (HAL)**: Direct interface with Sony proprietary `com.sony.scalar.hardware.CameraEx` and `CameraEx$ParametersModifier` on Sony BIONZ X (CXD90014) and legacy (CXD4132) image processors.
- **Input Pipeline**: Event propagation via `KeyReceiver` -> `BaseKeyHandler` -> `EachKeyDispatcher` -> `KeyConverter` -> `EachConvertedKeyDispatcher` -> `PictureEffectPlusOptionMenuLayout`.
- **Target Camera Matrix**:
  - Full-Frame Mirrorless: A7, A7R, A7S, A7M2, A7R2, A7S2
  - APS-C Mirrorless: A5100, A6000, A6300, A6500
  - Cyber-shot Compacts: RX100 M3/M4/M5, RX10 M2/M3, RX1R II, HX90
  - Legacy PMCA Gen 1: NEX-5R, NEX-5T, NEX-6

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Dynamic HAL Probing | Runtime capability detection for `setExtendedGammaTable`, `setRGBMatrix`, and WB registers | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Defensive RGB Matrix Fallback | Graceful degradation to RGB Matrix-only rendering when Gamma Table is unsupported or fails | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Defensive Neutral WB Fallback | Graceful fallback to neutral WB when WB shift registers fail or in unsupported WB modes | M1 | ORIGINAL_REQUEST §R1 |
| 4 | Safe DMA Memory Reclamation | Guaranteed native `GammaTable.release()` in try/finally to prevent kernel DMA heap exhaustion | M1 | ORIGINAL_REQUEST §R1 |
| 5 | Defensive Parameter Normalization | Safe execution of `setColorMode`, `setPictureEffect("off")`, `setDROMode`, `setHDRMode` | M1 | ORIGINAL_REQUEST §R1 |
| 6 | Original WB State Protection | Save and restore original user WB shift (`sOriginalLB`, `sOriginalCC`) on exit/reset | M1 | ORIGINAL_REQUEST §R1 |
| 7 | Multi-Dial / Dual-Dial Support | Map Front Dial (`0x20d/e`), Rear Dial (`0x210/1`), and Wheel to preset navigation without conflict | M2 | ORIGINAL_REQUEST §R2 |
| 8 | Triple-Dial Support | Map 3rd dial (`0x27a/b`) on 3-dial bodies (A7R2, A6500) to preset navigation | M2 | ORIGINAL_REQUEST §R2 |
| 9 | Single-Dial & D-Pad Adaptation | Unify Main Dial, Sub Dial, and 4-way D-Pad (Up/Down/Left/Right) for 1D preset cycling | M2 | ORIGINAL_REQUEST §R2 |
| 10 | RX Compact Lens Control Ring | Map lens ring CW/CCW (`0x288`/`0x289`) and FuncRing events to filter switching | M2 | ORIGINAL_REQUEST §R2 |
| 11 | Touch-Only Navigation (A5100) | Register with `TouchManager`, implement touch list item selection with D-pad fallback | M2 | ORIGINAL_REQUEST §R2 |
| 12 | Center Button Standardizing (`0xe8`) | Register-agnostic regex in `patch_apk.py` fixing Gen 1 (`v10`) vs Gen 2 (`v11`), bypassing custom key hijacking | M2 | ORIGINAL_REQUEST §R2 |
| 13 | Enter5Way / Joystick Fallback | Implement `pushedEnter5WayFuncKey` and `pushedEnterJoyStickFuncKey` returning `pushedCenterKey` | M2 | ORIGINAL_REQUEST §R2 |
| 14 | Dalvik Bytecode Verification | Ensure zero unresolvable static references on Android 2.3.7 API 10; register and local sanity | M3 | ORIGINAL_REQUEST §R3 |
| 15 | Dual-Compatible V1 JAR Signing | RFC 2315 PKCS#7 signing (`-noattr -binary -md sha1`), CRLF formatting, zero V2/V3 blocks | M3 | ORIGINAL_REQUEST §R3 |
| 16 | ZipAlign & Manifest Verification | 4-byte boundary alignment and `minSdkVersion: 10` compatibility in `AndroidManifest.xml` | M3 | ORIGINAL_REQUEST §R3 |
| 17 | Testbench Master Harness | Master automated test runner `tools/testbench/run_testbench.py` with exit codes and reporting | M0 | ORIGINAL_REQUEST §R4 |
| 18 | Tier 1 Dalvik Verification Test | Static bytecode verifier checking smali syntax, locals, registers, and Dalvik API 10 rules | M0 | ORIGINAL_REQUEST §R4 |
| 19 | Tier 2 PMCA Symbol Auditor | Framework symbol compatibility checker against Gen 1 and Gen 2 framework dumps | M0 | ORIGINAL_REQUEST §R4 |
| 20 | Tier 3 Input Ergonomics Simulator | Automated synthetic event stream tests verifying dial, ring, touch, and center button handling | M0 | ORIGINAL_REQUEST §R4 |
| 21 | Tier 4 APK Packaging Validator | Automated verification of V1 JAR signature, SHA-1 digest, and Apache Harmony compatibility | M0 | ORIGINAL_REQUEST §R4 |
| 22 | Mock PMCA Framework Dumps | Reference symbol catalogs (`gen1_symbols.json`, `gen2_symbols.json`) in `tools/testbench/` | M0 | ORIGINAL_REQUEST §R4 |
| 23 | E2E Suite Pass & Non-Regression | 100% pass across all testbench tiers and zero regressions on real A6300 hardware | M_FINAL | ORIGINAL_REQUEST Acceptance |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Testbench Infrastructure | Construct automated cross-model static verification testbench in `tools/testbench/` (Features 17-22) | None | IN_PROGRESS |
| M1 | Dynamic HAL Probing & Degradation | Implement dynamic probing, defensive reflection, RGB Matrix fallback, WB fallback, DMA memory safety in `RicohHook.smali` (Features 1-6) | None | PLANNED |
| M2 | Universal Hardware Control | Multi-dial, RX lens ring, A5100 touch, center button `0xe8` regex patch across Gen 1 & Gen 2 (Features 7-13) | None | PLANNED |
| M3 | Cross-Platform Runtime & Packaging | Dalvik verification compliance, RFC 2315 V1 JAR signer in `tools/sign_apk.py`, zipalign (Features 14-16) | None | PLANNED |
| M_FINAL | E2E Validation & Hardening | Pass 100% of testbench suite (Tiers 1-4), adversarial test hardening (Tier 5), and final verification (Feature 23) | M0, M1, M2, M3 | PLANNED |

## Interface Contracts

### `RicohHook` ↔ Camera HAL
- `probeCapabilities(CameraEx cameraEx, ParametersModifier modifier)`: Probes `isExtendedGammaTableSupported()`, `isRGBMatrixSupported()`, and WB shifts. Sets static capability flags.
- `applyHook(PictureEffectPlusController controller, Pair<Parameters, ParametersModifier> pair, String presetId) -> boolean`: Executes defensive normalization, WB shift with neutral fallback, RGB matrix, and 10-bit Gamma Table with RGB-only fallback and `finally { table.release(); }`.
- `resetHook(PictureEffectPlusController controller, Pair<Parameters, ParametersModifier> pair) -> void`: Restores `setExtendedGammaTable(null)`, bypasses matrix, and restores original WB.

### `KeyConverter` ↔ Input Dispatch
- ScanCode `0xe8` (Center Button): If `code == 0xe8`, set key object reference to `null` before querying custom function, forcing `CustomizableFunction.Unchanged` -> `EachConvertedKeyDispatcher` -> `pushedCenterKey()`.
- ScanCodes `0x204`, `0x206`, `0x203`, `0xcf`, `0x26e`, `0x26f`: Must remain completely untouched.

### `PictureEffectPlusOptionMenuLayout` ↔ Hardware Controls
- Methods implemented / overridden:
  - `turnedMainDialNext() -> pushedDownKey()`
  - `turnedMainDialPrev() -> pushedUpKey()`
  - `turnedSubDialNext() -> pushedDownKey()`
  - `turnedSubDialPrev() -> pushedUpKey()`
  - `turnedThirdDialNext() -> pushedDownKey()`
  - `turnedThirdDialPrev() -> pushedUpKey()`
  - `turnedRingClockwise() -> pushedDownKey()`
  - `turnedRingCounterClockwise() -> pushedUpKey()`
  - `turnedFuncRingNext() -> pushedDownKey()`
  - `turnedFuncRingPrev() -> pushedUpKey()`
  - `onTouchEvent(MotionEvent) / TouchManager`: selects item on touch, confirms on tap.

### `tools/testbench` ↔ CI & Build Validation
- Invocation: `python3 tools/testbench/run_testbench.py [--apk <path>] [--smali <path>]`
- Return code: `0` on 100% pass across all tiers; non-zero with failure diagnostic on any tier failure.

## Code Layout
- `src/smali/com/sony/imaging/app/pictureeffectplus/shooting/camera/RicohHook.smali`: Core defensive HAL hook.
- `tools/generate_ricoh_hook.py`: Generator script for `RicohHook.smali` and binary gamma tables.
- `tools/patch_apk.py`: Automated smali and resource patcher for official Sony APKs.
- `tools/sign_apk.py`: RFC 2315 PKCS#7 V1 JAR signer.
- `tools/testbench/`: Automated cross-model static verification testbench.
  - `run_testbench.py`: Master test runner.
  - `test_dalvik_verification.py`: Tier 1 bytecode validator.
  - `test_pmca_symbols.py`: Tier 2 framework symbol auditor.
  - `test_input_ergonomics.py`: Tier 3 input simulation harness.
  - `test_apk_signing.py`: Tier 4 signature & packaging validator.
  - `mock_pmca_framework/`: Gen 1 & Gen 2 symbol catalogs.
