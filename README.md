# Sony PMCA Ricoh Film Simulation Camera Mod

<p align="center">
  <strong>English</strong> |
  <strong><a href="README.zh-CN.md">简体中文</a></strong> |
  <strong><a href="README.zh-TW.md">繁體中文</a></strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Sony%20PMCA%20%2F%20Android%204.1.2-blue?style=flat-square" alt="Platform">
  <img src="https://img.shields.io/badge/Hardware%20ISP-Zero%20Lag%20%2F%20Burst%20OK-brightgreen?style=flat-square" alt="Hardware ISP">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Version-v1.3.0--B2.1-orange?style=flat-square" alt="Version">
</p>

Deeply transforms Sony's official "Picture Effect+" PlayMemories Camera App into a native-level **"Ricoh Camera"** through low-level hardware ISP hook and reverse engineering. By directly programming the **pre-ISP hardware White Balance shifts (LB/CC), 1024-point non-linear Gamma tone curves (with baked EV compensation), and row-sum normalized 3×3 RGB color matrices** into camera hardware registers, it faithfully reproduces the signature Ricoh GR split toning and filmic weight—delivering **zero shutter lag, artifact-free real-time EVF/LCD preview, and native high-speed continuous burst shooting**.

---

## 🌟 Key Features & Highlights

- ⚡ **Pure Hardware ISP Real-time Pipeline**:
  Directly interfaces with Sony's proprietary library `com.sony.scalar.hardware.CameraEx` to write directly to hardware registers. Still capture executes via `SingleProcess` $\rightarrow$ `CameraEx.burstableTakePicture()`, completely bypassing slow software CPU RAW processing. Autofocus, shutter trigger, burst shooting, and live view operate with zero added latency.
- 🌐 **Runtime Adaptive Multi-Language Engine (Zero-Config)**:
  - Dynamically perceives camera system locale via `Locale.getDefault()` without requiring separate APKs.
  - Seamlessly and automatically renders native translations across app launcher icons, live view OSD badges, option menus, dial scrolling indicators, and help guides:
    - **English & International**: `Ricoh Camera`, `Ricoh GR Positive Film`, `Ricoh Negative Film`, `High Contrast B&W`, `Moriyama Daido B&W`, `Cross Process`.
    - **繁體中文 (台灣 / 香港)**: `理光相機`, `理光 GR 正片`, `理光 負片`, `高對比黑白`, `森山大道風`, `正負逆沖`.
    - **简体中文 (大陆)**: `理光相机`, `理光 GR 正片`, `理光 负片`, `高对比黑白`, `森山大道风`, `正负逆冲`.
- 🌈 **Authentic Ricoh Split Toning & Color Reproduction**:
  - **Pre-ISP Hardware WB Shifts**: Injects precise LB (Light Balance / amber-blue) and CC (Color Compensation / green-magenta) offsets, providing a warm slide base or gentle vintage negative undertone. Automatically restores user original WB upon exiting the app.
  - **1024-Point Gamma Curve with Baked EV**: Baked -0.33 EV under-exposure in Positive Film and Moriyama B&W suppresses harsh blown-out highlights; baked +0.33 EV boost with lifted black floor in Negative Film replicates wide dynamic latitude analog print look.
  - **Row-Sum Normalized 3×3 Color Matrix**: Working in synergy with pre-WB offsets and S-curves to achieve the hallmark Ricoh GR3 split toning: *"Cool cyan shadows, warm amber highlights"*.
- 🎨 **5 Signature Ricoh & Street Film Presets**:
  - **Ricoh Positive Film**: Authentic Ricoh GR Positive Film profile, decoupled from Sony's built-in creative styles. Features saturated cyan-blue skies, yellow-green foliage, gentle film contrast, and nuanced shadow gradations without clipping.
  - **Ricoh Negative Film**: Matte film tone curve with lifted black level (~36), low contrast, subtle warm cast, and graceful highlight roll-off.
  - **High Contrast B&W**: Accurate BT.601 luminance grayscale conversion combined with an aggressive S-curve, yielding an inky, high-density street look.
  - **Moriyama Daido Style**: Heavy red-filter weighted monochrome channel mix, darkening blue skies, producing dramatic grain structure and raw monochrome street tension.
  - **Cross Process**: Stylized analog cross-processing curve with cyan/magenta shifts in dark tones and warm yellow-greens in highlights.
- 🔄 **Hardware Color State Protection**: Automatically resets identity matrices, WB shift registers, and default Gamma curves upon filter switching or application exit, preventing any persistent color cast on camera restarts.

---

## 📷 Supported Cameras (PMCA Architecture)

Compatible with all Sony mirrorless and compact cameras supporting the PlayMemories Camera Apps (PMCA) platform:

| Series | Supported Models |
|:---|:---|
| **APS-C Mirrorless** | A5100, A6000, A6300, A6500 |
| **Full-Frame Mirrorless** | A7, A7R, A7S, A7M2 (A7II), A7R2 (A7RII), A7S2 (A7SII) |
| **Cyber-shot / Compacts** | RX100 M3 / M4 / M5, RX10 M2 / M3, RX1R II, HX90, etc. |

> **Note**: Gen 3/4/5 Sony cameras (such as A7M3, A7C, A6400, A6700, etc.) no longer run PMCA/Android and are not supported.

---

## 🚀 Quick Start & Installation

### Prerequisites
1. Ensure the `adb` command-line tool is installed on your computer:
   - macOS: `brew install android-platform-tools`
   - Linux: `sudo apt-get install adb`
   - Windows: Download [Google SDK Platform Tools](https://developer.android.com/tools/releases/platform-tools) and add to PATH.
2. Turn on camera Wi-Fi and launch the ADB daemon (default port 5555).
3. Connect your computer and camera to the same Wi-Fi network and obtain the camera IP address (e.g., `192.168.1.100`).

### Method 1: One-Click Wi-Fi ADB Install (Recommended)

Clone this repository and run the bundled deployment script:

```bash
git clone https://github.com/bonyback1/sony-pmca-ricoh-mod.git
cd sony-pmca-ricoh-mod

# One-click install to camera (replace with your camera's IP)
./scripts/install.sh 192.168.1.100
```

> **Tip**: If no IP argument is provided, the script interactively prompts for the address and automatically locates the latest APK.

### Method 2: Via PMCA-GUI Flashing Tool
You can also use the open-source [pmca-gui](https://github.com/ma1co/Sony-PMCA-RE) tool via a USB cable to flash the packaged APK directly onto the camera.

---

## 🛠️ Advanced Development: Automated Patch Pipeline

This project includes a fully automated patch and build pipeline allowing users to customize and build from official base packages:

```bash
# 1. Ensure apktool and python3 are installed
brew install apktool

# 2. Run the one-click build pipeline
python3 tools/patch_apk.py -i /path/to/Sony_PictureEffectPlus.apk -o Ricoh_Camera.apk
```

The pipeline automatically carries out:
1. **Decompilation**: Unpacks base APK using `apktool d -r` (preserving binary resources to avoid aapt private symbol collisions).
2. **Hook Injection**: Injects `src/smali/RicohHook.smali` into the application controller layer.
3. **Smali Patching**: Applies control flow hooks to `PictureEffectPlusController.smali`, `BaseMenuService.smali`, `PictureEffectPlusOptionMenuLayout.smali`, and `AppRoot.smali`.
4. **Menu Localization & Ordering**: Rewrites `assets/MenuData.xml` to inject Ricoh preset titles and elevate them to top priority.
5. **Recompilation**: Rebuilds `classes.dex` and the final APK container via `apktool b`.
6. **Legacy Signature Compatibility**: Runs `tools/sign_apk.py` to generate Android 4.1.2-compatible v1 JAR signatures.

---

## 🔬 Architecture & Reverse Engineering Insights

For in-depth technical analysis and register maps, see [SONY_A6300_RICOH_FILTER_MOD_GUIDE.md](docs/SONY_A6300_RICOH_FILTER_MOD_GUIDE.md). Below are key engineering pitfalls and resolutions:

1. **USB PMCA Official Whitelist Signature Verification**:
   - *Symptom*: USB flashing aborts at `Installing 0%` with `Communication error 100`.
   - *Root Cause*: Sony daemon `scalarainstaller` strictly checks master keys for `com.sony.*` packages.
   - *Fix*: Install via Wi-Fi ADB directly targeting the underlying Android Package Manager, completely bypassing the vendor installer verification.
2. **macOS 15+ (Sequoia) Local Network Privacy Restrictions**:
   - *Symptom*: `adb connect <IP>:5555` fails with `No route to host` (Errno 65).
   - *Root Cause*: macOS Sequoia requires explicit local network permissions for terminal and CLI processes.
   - *Fix*: Grant local network access in *System Settings $\rightarrow$ Privacy & Security $\rightarrow$ Local Network* for your terminal/IDE.
3. **Android 4.1.2 Certificate Signature Compatibility**:
   - *Symptom*: `INSTALL_PARSE_FAILED_NO_CERTIFICATES`.
   - *Root Cause*: Modern JDK 21+ `jarsigner` injects modern CMS protection attributes (`id-aa-cmsAlgorithmProtect`), which Sony's 2012 Apache Harmony cryptographic stack cannot parse.
   - *Fix*: Use `tools/sign_apk.py` (built on clean OpenSSL smime `-noattr -binary`).
4. **Dalvik Dexopt Bytecode Verification Constraints**:
   - *Symptom*: `INSTALL_FAILED_DEXOPT` with error `Bogus method access flags 29 @ 5`.
   - *Root Cause*: Dalvik DEX specifications forbid non-native methods from having `ACC_SYNCHRONIZED (0x20)` in method headers.
   - *Fix*: Smali code strictly uses explicit `monitor-enter` / `monitor-exit` pairs instead of synchronized method access flags.
5. **Native DeviceBuffer DMA Memory Leak Prevention**:
   - *Symptom*: Intermittent camera freezing or viewfinder lockup when switching presets or viewing photos rapidly.
   - *Root Cause*: `CameraEx$GammaTable` allocates physical DMA display memory; unreleased tables exhaust kernel buffer pools.
   - *Fix*: Strictly call `table.release()` immediately after submitting buffers to the HAL.

---

## 📂 Project Structure

```text
├── .github/
│   ├── workflows/ci.yml       # Continuous integration automated test workflow
│   └── ISSUE_TEMPLATE/        # Issue and feature request templates
├── docs/                      # Core technical guides and documentation
│   ├── SONY_A6300_RICOH_FILTER_MOD_GUIDE.md
│   └── A6300连接手机App指南.md
├── src/                       # Open-source source code
│   ├── smali/RicohHook.smali  # Hardware ISP register injection core class
│   ├── patches/               # Smali controller patch diffs
│   └── luts/                  # Classic Ricoh film 3D LUT profiles (.CUB)
├── tools/                     # Cross-platform development toolchain
│   ├── patch_apk.py           # Automated decompile, inject, recompile & sign pipeline
│   ├── sign_apk.py            # Android 4.1.2 compatible v1 signing tool
│   ├── generate_ricoh_hook.py # Smali generator for Gamma curves & matrices
│   └── update_menu_data.py    # Menu XML automated modifier
├── scripts/
│   └── install.sh             # Wi-Fi ADB one-click deployment script
├── .gitignore                 # Git ignore rules (isolates proprietary binaries & keys)
├── CHANGELOG.md               # Version history
├── LICENSE                    # Apache 2.0 license & disclaimer
├── README.md                  # English Documentation (Default)
├── README.zh-CN.md            # Simplified Chinese Documentation
└── README.zh-TW.md            # Traditional Chinese Documentation
```

---

## 📜 Disclaimer

1. This project is an independent open-source reverse engineering and color science research project for study, educational, and technical exchange purposes only.
2. "Sony", "PlayMemories Camera Apps", "PMCA", "Ricoh", and "GR" are registered trademarks of their respective owners. This project is not affiliated with, endorsed by, or sponsored by Sony Corporation or Ricoh Company, Ltd.
3. Please respect local copyright laws. Do not redistribute proprietary vendor binaries. Any software or hardware modifications performed using these tools are done entirely at your own risk.

---

## 🤝 Contributing & Community

Contributions via Issues and Pull Requests are warmly welcome!
- Share color science measurements for more classic film simulations (Fujifilm Classic Negative, Kodak Gold, Leica Monochrome, etc.).
- Report hardware compatibility and test results across different Sony camera bodies.
