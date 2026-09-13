# Sony PMCA Testbench: Cross-Model Static Verification Suite (M0 Complete)

**Status**: Verified & Production-Ready  
**Milestone**: M0 - Testbench Infrastructure  
**Author**: `worker_m0_1`  
**Execution Entry Point**: `tools/testbench/run_testbench.py`

---

## 1. Overview & Architecture

The cross-model static verification testbench provides automated, deterministic quality assurance for the modded Ricoh camera application (`com.sony.imaging.app.pictureeffectplus`) across all Sony PlayMemories Camera Apps (PMCA) camera hardware profiles.

It covers:
- **PMCA Gen 1 (Android 2.3.7 / API 10 / Gingerbread / CXD4132)**: NEX-5R, NEX-5T, NEX-6
- **PMCA Gen 2 (Android 4.1.2 / API 16 / Jelly Bean / BIONZ X CXD90014)**:
  - Full-Frame Mirrorless: A7, A7R, A7S, A7M2, A7R2, A7S2
  - APS-C Mirrorless: A5100, A6000, A6300, A6500
  - Cyber-shot Compacts: RX100 M3/M4/M5, RX10 M2/M3, RX1R II, HX90

```
tools/testbench/
├── __init__.py
├── run_testbench.py                  # Master test runner CLI, ASCII summary & JSON reporter
├── test_dalvik_verification.py       # Tier 1: Dalvik API 10 bytecode & static verifier
├── test_pmca_symbols.py              # Tier 2: PMCA Gen 1 vs Gen 2 framework symbol auditor
├── test_input_ergonomics.py          # Tier 3: Multi-model input & event stream simulator
├── test_apk_signing.py               # Tier 4: Dual-compatible APK packaging & V1 signer validator
└── mock_pmca_framework/             # Reference framework symbol catalogs
    ├── gen1_symbols.json
    └── gen2_symbols.json
```

---

## 2. Verification Tiers & Checks

### Tier 1: Dalvik API 10 Static Bytecode Verifier (`test_dalvik_verification.py`)
Audits Smali bytecode against Android 2.3.7 Dalvik runtime constraints:
1. **Smali Syntax & Assembler Dry-Run**: Validates lexical block balance (`.method`/`.end method`, switch blocks, array data), branch label resolution, and optional `apktool b` dry-run assembly.
2. **Register Bounds & `.locals` Declaration Audit**: Parses method signatures, computes parameter registers (including 64-bit wide register pairs for `J` and `D`), and enforces strict register frame bounds (`v0..v(M-1)`).
3. **Dalvik API 10 Opcodes & Virtual Invocation Safety**: Enforces opcode whitelist forbidding modern ART opcodes (`invoke-polymorphic`, `invoke-custom`, `const-method-handle`, etc.), restricts constructor `<init>` to `invoke-direct`, forbids `<clinit>` invocation, guards against Dalvik API 10 interface method bug (`Object` methods on interfaces), and verifies return opcode vs descriptor consistency.
4. **Catchall Ordering & Exception Handlers**: Enforces canonical Dalvik try-catch ordering (forbids typed `.catch` following `.catchall`, flags shadowed handlers), enforces `move-exception` as the first instruction of handlers, and forbids `move-exception` outside handlers.
5. **Register Type Conflict Detection**: Forward fixpoint abstract interpretation on CFG lattice (`UNINIT`, `REF`, `PRIM32`, `PRIM64_LO`, `PRIM64_HI`, `NULL_CONST`, `CONFLICT`), preventing register merge conflicts across branches.

### Tier 2: PMCA Framework Symbol Auditor (`test_pmca_symbols.py`)
Cross-references Dalvik invocations against reference firmware dumps (`gen1_symbols.json` vs `gen2_symbols.json`):
1. **Universal Framework Symbol Audit**: Audits `CameraEx`, `CameraEx$ParametersModifier`, `CameraEx$GammaTable`, `CameraSetting`, `BaseMenuService`, and `AppRoot`.
2. **Gen 1 Crash Hazard & Defensive Guard Audit**: Ensures every Gen 2-only method (`setRGBMatrix`, `createGammaTable`, `setExtendedGammaTable`, `GammaTable.release`) is either dynamically reflected via `Method.invoke` or enclosed in a non-rethrowing `Throwable` try-catch block with graceful fallback.
3. **Fragile HAL Hardware Protection Audit**: Verifies that calls to sensitive hardware registers (`setLightBalanceForWhiteBalance`, `setColorCompensationForWhiteBalance`, `setColorMode`, `setDROMode`, `setHDRMode`) possess defensive try-catch error recovery.
4. **DMA Memory Safety Audit**: Ensures native DMA memory allocations (`createGammaTable`) guarantee native cleanup (`GammaTable.release`) in a `finally` block to prevent kernel DMA slab exhaustion.

### Tier 3: Input Ergonomics Simulator (`test_input_ergonomics.py`)
Simulates synthetic hardware event streams across 5 camera ergonomics profiles:
1. **Dual-Dial / Multi-Dial Bodies (A7 series, A6500)**: Verifies Front Dial (`0x20d/e`), Rear Dial (`0x210/1`), Sub-Dial/Wheel (`0x20a/b`), and 3rd Dial (`0x27b/a`) operate without conflict during interleaved turns.
2. **Single-Dial Bodies (A6000, A6300)**: Verifies Main Dial, Sub-Dial, and 4-way D-pad 1D preset cycling (Right/Down = next, Left/Up = prev) with boundary wrapping.
3. **RX Compact Lens Ring (RX100 M3-M5, RX10 M2/M3, RX1R II)**: Verifies lens control ring CW (`0x288`) and CCW (`0x289`) and FuncRing events.
4. **Touch-Only Bodies (A5100)**: Verifies touchscreen item selection on tap, repeat-tap confirmation (`pushedCenterKey`), and uninterrupted physical fallbacks.
5. **Center Button (`0xe8`) Bypass & Key Preservation**: Audits register-agnostic `KeyConverter` regex across Gen 1 (`v10`) and Gen 2 (`v11`), verifying that customized center button assignments are bypassed while Shutter S1/S2 (`0x204/0x206`), Movie Rec (`0x203/0x27d`), Playback (`0xcf`), and Custom keys (`0x26e/0x26f`) are strictly preserved.

### Tier 4: APK Packaging & Signing Validator (`test_apk_signing.py`)
Validates dual-compatible APK packaging for legacy PMCA package managers:
1. **ZIP Structure & META-INF V1 Signatures**: Verifies `MANIFEST.MF`, single `.SF`, single `.RSA`/`.DSA`, and MIME folded-line header compliance.
2. **MANIFEST.MF SHA-1 Digest Integrity**: Verifies pure SHA-1 digests across all entries; strictly forbids `SHA-256-Digest:` entries that cause `INSTALL_PARSE_FAILED_NO_CERTIFICATES` on Android 2.3.7.
3. **Absence of APK Signature Scheme v2/v3**: Verifies absence of `b"APK Sig Block 42"` before the Central Directory and across the APK archive.
4. **Absence of CMS Signed Attributes**: Verifies `CERT.RSA` is pure RFC 2315 PKCS#7 without CMS attributes (OID `1.2.840.113549.1.9.52`, `signingTime`, `messageDigest`) that trigger Apache Harmony `JarVerifier` rejections.
5. **4-Byte ZipAlign Boundary Verification**: Ensures all stored uncompressed entries, especially `resources.arsc`, are 4-byte aligned for zero-copy memory mapping (`mmap`).

---

## 3. Command Line Interface

```bash
# Display help and options
python3 tools/testbench/run_testbench.py --help

# Run all tiers (Tier 1, Tier 2, Tier 3, Tier 4)
python3 tools/testbench/run_testbench.py --tier all

# Run specific tiers (e.g. Tier 1 & Tier 3)
python3 tools/testbench/run_testbench.py --tier 1,3

# Run with verbose diagnostic traces
python3 tools/testbench/run_testbench.py --tier 1 -v

# Target specific APK and smali directory
python3 tools/testbench/run_testbench.py --apk PictureEffectPlus_Ricoh_Compat.apk --smali-dir src/smali

# Export machine-readable JSON report
python3 tools/testbench/run_testbench.py --json-report test_report.json
```

### Exit Codes
- `0`: 100% of all executed checks passed.
- `1`: One or more verification checks failed.
- `2`: CLI argument error or invalid configuration.

---

## 4. Self-Test Fixture Commands

Each tier module provides a standalone `--fixtures` self-test suite confirming both positive and negative defect detection:

```bash
# Tier 1 Dalvik Verifier Fixtures
python3 tools/testbench/test_dalvik_verification.py --fixtures

# Tier 2 Symbol Auditor Fixtures
python3 tools/testbench/test_pmca_symbols.py --fixtures

# Tier 3 Input Ergonomics Simulator
python3 tools/testbench/test_input_ergonomics.py

# Tier 4 APK Signing Validator Fixtures
python3 tools/testbench/test_apk_signing.py --fixtures
```

---

## 5. Milestone Verification Readiness

With Milestone M0 complete, the testbench stands ready to independently audit subsequent implementation milestones:
- **Milestone M1**: Will resolve Tier 2 Gen 1 crash hazards by implementing dynamic HAL probing and defensive reflection in `RicohHook.smali`.
- **Milestone M2**: Will implement hardware control ergonomics in `PictureEffectPlusOptionMenuLayout.smali` and `KeyConverter.smali`.
- **Milestone M3**: Will resolve Tier 4 ZipAlign and packaging constraints in `tools/sign_apk.py`.
- **Milestone M_FINAL**: Will achieve 100% PASS across all 19 checks in Tiers 1 through 4.
