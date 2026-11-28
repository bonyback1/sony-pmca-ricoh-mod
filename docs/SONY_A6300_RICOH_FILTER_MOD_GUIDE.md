# Technical Architecture Guide: Sony PMCA "Picture Effect+" to "Ricoh Camera" Mod

> **Verification Status**: Verified on Sony ILCE-6300 (Firmware v2.01 / Android 4.1.2) and cross-checked across PMCA Gen 1 & Gen 2 symbol sets via the automated 5-Tier testbench.

---

## 1. Overall Architecture & Color Rendering Pipeline

Sony's official PlayMemories Camera App "Picture Effect+" uses two rendering pipelines under the hood:

1. **Pure Hardware ISP Real-Time Pipeline (Zero Shutter Lag, Low Power, Burst Compatible)**:
   - Single-step effects write directly to camera hardware ISP registers via Sony's proprietary library `com.sony.scalar.hardware.CameraEx`.
   - Still capture executes through `SingleProcess` $\rightarrow$ `CameraEx.burstableTakePicture()`, completely bypassing slow CPU-side RAW development. Autofocus, shutter trigger, continuous burst shooting, and EVF/LCD live view all operate with native zero lag.

2. **Hardware Parameter Definitions for the 5 Film Presets**:
   - **Ricoh GR Positive Film** (slot `pop-color`):
     - Decomposed from `GR3-P-V3 Plady.cube` into a 1024-point 10-bit `ExtendedGammaTable` and row-sum normalized 3×3 Q10 RGB matrix.
   - **Ricoh Negative Film** (slot `retro-photo`):
     - Decomposed from `GR3-N-V3 Plady.cube` with lifted matte black floor, gentle contrast, and subtle warm negative cast.
   - **High Contrast B&W** (slot `richtone-mono`):
     - BT.601 luminance grayscale matrix (`[306, 601, 117]` per row) paired with an aggressive S-curve for deep inks and crisp highlights.
   - **Moriyama Daido Style** (slot `rough-mono`):
     - Red-filter weighted monochrome matrix (`[563, 358, 103]` per row) darkening skies and crushing shadows with `-0.33 EV` baked in.
   - **Steve McCurry Kodachrome** (slot `watercolor`):
     - Decomposed from `Leica_SteveMcCurry.cube` with pure slide blacks ($D_{\min} = 0$), dense shadow gradations, and calibrated color matrix.
   - **Hardware State Sanitization**:
     - On filter switch or exit, `resetHook()` clears `setColorSelectMode("off", sEmptyIntArray)`, resets `setExtendedGammaTable(null)`, restores the 3×3 Identity Matrix `[1024, 0, 0, 0, 1024, 0, 0, 0, 1024]`, and restores the user's backed-up Creative Style, Contrast, Saturation, Sharpness, DRO, HDR, and White Balance shifts.

---

## 2. Reverse Engineering & Smali Hook Injection

### Business Logic & Smali Hooks
- Target controller: `com.sony.imaging.app.pictureeffectplus.shooting.camera.PictureEffectPlusController`
- Core dispatch hook: `setPlusPictureEffect(Ljava/lang/String;)Z`
- Helper class: `com.sony.imaging.app.pictureeffectplus.shooting.camera.RicohHook`
- When a Ricoh preset ID is selected:
  1. Disables Sony's native Picture Effect (`setPictureEffect("off")`) to eliminate hardware channel conflicts.
  2. Backs up the user's pre-existing camera parameters from live `CameraSetting.getParameters()`.
  3. Injects pre-ISP White Balance offsets, the 1024-point `ExtendedGammaTable` (releasing the native `DeviceBuffer` immediately after submission), and the 3×3 `RGBMatrix`.
  4. Commits `CameraSetting.setParameters(...)` and skips Sony's default effect application path.
- **Dexopt Stability Rule**: Non-native methods in `RicohHook.smali` must **never** use the `ACC_SYNCHRONIZED (0x20)` method flag (which causes `INSTALL_FAILED_DEXOPT` / `Bogus method access flags 29`). Use explicit `monitor-enter` / `monitor-exit` blocks if synchronization is needed.

---

## 3. Four Key Engineering Pitfalls & Solutions

### Pitfall 1: USB PMCA Whitelist Signature Verification
- **Symptom**: USB installation via `pmca-console install` aborts at `Installing 0%` with `Communication error 100`.
- **Root Cause**: Sony's `scalarainstaller` daemon verifies Sony's master signature for `com.sony.*` packages.
- **Solution**: Install over Wi-Fi ADB directly via Android's `pm` installer (`./scripts/install.sh`), bypassing the vendor USB installer check.

### Pitfall 2: macOS Sequoia (15+) Local Network Privacy Block
- **Symptom**: `adb connect <CAMERA_IP>:5555` fails with `No route to host` (Errno 65).
- **Root Cause**: macOS 15+ enforces Local Network privacy permissions per terminal/binary.
- **Solution**: `scripts/install.sh` includes an automated Python TCP relay (`127.0.0.1:15555 -> <CAMERA_IP>:5555`), or grant Local Network access in *System Settings → Privacy & Security → Local Network*.

### Pitfall 3: Android 4.1.2 Certificate Parsing Compatibility
- **Symptom**: `adb install` fails with `INSTALL_PARSE_FAILED_NO_CERTIFICATES` (`Incorrect signature at JarUtils.verifySignature`).
- **Root Cause**: Modern JDK `jarsigner` injects CMS attributes (`id-aa-cmsAlgorithmProtect`) that Android 4.1.2's 2012 Apache Harmony stack cannot parse.
- **Solution**: Sign with `tools/sign_apk.py` (clean OpenSSL `smime -noattr -binary` pure V1 JAR signature + 4-byte ZipAlign).

### Pitfall 4: Dalvik Dexopt Method Access Flag Verification
- **Symptom**: `adb install` fails with `INSTALL_FAILED_DEXOPT` (`E/dalvikvm: Bogus method access flags 29 @ 5`).
- **Root Cause**: Dalvik DEX forbids `ACC_SYNCHRONIZED (0x20)` on non-native method headers.
- **Solution**: Declare `.method public static` without `synchronized` and use `monitor-enter` / `monitor-exit` inside the method body if needed.

---

## 4. Automated Build & Verification

Run the automated build and 5-tier verification suite from the repository root:

```bash
python3 tools/patch_apk.py -i official_apks/Sony_A6300_pictureeffectplus.apk -o PictureEffectPlus_Ricoh.apk
python3 tools/testbench/run_testbench.py
./scripts/install.sh <CAMERA_IP> PictureEffectPlus_Ricoh.apk
```
