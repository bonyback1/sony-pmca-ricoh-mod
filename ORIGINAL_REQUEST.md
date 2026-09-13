# Original User Request

## Initial Request — 2026-09-13T00:50:23Z

Ensure the modded Ricoh Camera application (`com.sony.imaging.app.pictureeffectplus`) operates reliably with universal hardware compatibility across all Sony PlayMemories Camera Apps (PMCA) camera models—spanning APS-C mirrorless (A5100, A6000, A6300, A6500), Full-Frame mirrorless (A7, A7R, A7S, A7M2, A7R2, A7S2), and Cyber-shot compacts (RX100 M3/M4/M5, RX10 M2/M3, RX1R II, HX90)—using defensive runtime architecture and cross-model static firmware auditing.

Working directory: `/Users/zhuqi/Documents/a6300`
Integrity mode: development

References:
- OpenMemories PMCA Developer Bible: https://github.com/up209d/open-memories-app-ai/blob/main/Bible.md
- Sony CameraEx private HAL specifications and PMCA Gen 1 (Android 2.3) / Gen 2 (Android 4.1.2) platform differences

## Requirements

### R1. Dynamic HAL Hardware Capability Probing & Graceful Degradation
Implement dynamic runtime detection for all hardware registers (`setExtendedGammaTable`, `setRGBMatrix`, `setLightBalanceForWhiteBalance`, `setColorCompensationForWhiteBalance`, `setColorMode`, etc.):
- If an older PMCA firmware or entry-level camera HAL does not support 10-bit Gamma tables or WB shifts, the app must gracefully degrade without throwing `NoSuchMethodError`, `IncompatibleClassChangeError`, or unhandled native exceptions.
- Provide defensive fallback execution paths (e.g. RGB Matrix-only rendering if Gamma table allocation fails, or neutral WB shift if White Balance registers are unavailable).

### R2. Universal Hardware Control & Event Adaptation
Ensure intuitive filter switching and menu navigation across all PMCA control ergonomics:
- **Dual-Dial / Multi-Dial Bodies (A7 series, A6500)**: Support front dial, rear dial, and sub-dial without conflict.
- **Single-Dial Bodies (A6000, A6300)**: Support main dial, sub-dial, and 4-way direction pad.
- **Compact Cameras with Control Rings (RX100 M3/M4/M5, RX10 M2/M3, RX1R II)**: Map lens control ring (`turnedSubDialNext` / `turnedSubDialPrev` or ring events) and control wheel to filter switching.
- **Touch-Only Bodies (A5100)**: Provide accessible on-screen touch targets or standard button fallbacks for models lacking physical dials and EVF.
- **Center Button & Custom Keys**: Standardize center button scanCode handling (`0xe8` vs other Sony keycodes) across Gen 1 and Gen 2 key converters.

### R3. Cross-Platform Android Runtime & APK Packaging Compatibility
Ensure the compiled and signed APK satisfies the runtime constraints of both PMCA Gen 1 (Android 2.3.7 / API 10) and PMCA Gen 2 (Android 4.1.2 / API 16):
- Strict adherence to Dalvik bytecode verification rules (zero unresolvable static references on older runtimes, zero invalid opcode usage).
- Verified dual-compatible APK signing: standard V1 JAR signing (SHA-1 with RSA) with valid timestamp and digest headers accepted by legacy PMCA package managers.
- Proper Manifest flags and permissions compatible across all target devices.

### R4. Automated Cross-Model Static Verification Testbench
Construct an automated testbench in `tools/` that audits the generated APK against known PMCA camera framework dumps:
- Validate class, method, and field signatures against PMCA framework classes (`com.sony.scalar.hardware.CameraEx`, `CameraEx$ParametersModifier`, `CameraSetting`, `BaseMenuService`, `AppRoot`).
- Run static Dalvik bytecode verification (`dexopt` / `baksmali` syntax and verification checks).
- Run automated simulation tests verifying dial rotation, center button press, and locale switching.

## Acceptance Criteria

### Hardware API Resilience & Safety
- [ ] All `CameraEx` and `ParametersModifier` invocations are guarded by dynamic reflection or `Throwable` try-catch blocks with verified fallback branches.
- [ ] Simulated absence of `setExtendedGammaTable`, `setRGBMatrix`, or `setLightBalanceForWhiteBalance` causes zero unhandled crashes and produces a documented fallback output.
- [ ] Memory buffer reclamation (`GammaTable.release()`) executes safely on devices with and without DMA table support.

### Multi-Model Input Navigation
- [ ] Directional pad (Up/Down/Left/Right), dials (Main/Sub/Front/Rear), lens ring, and center button all navigate presets predictably.
- [ ] Touch events in `OptionMenuLayout` work on touch-enabled models (A5100).
- [ ] KeyConverter patches do not intercept or break unrelated camera buttons (Shutter S1/S2, Movie Rec, Playback, C1/C2).

### Packaging & Compatibility Verification
- [ ] `apktool b` builds without errors, and `apksigner verify` confirms valid V1 (JAR) signature.
- [ ] Static symbol checker script passes with 0 missing required symbols across all PMCA target models.
- [ ] Real-camera installation and execution on A6300 remains 100% functional with zero regressions in image processing or performance.
