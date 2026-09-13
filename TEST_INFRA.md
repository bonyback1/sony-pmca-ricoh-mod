# E2E Test Infra: Sony PMCA Ricoh Camera Mod

## Test Philosophy
- Opaque-box, requirement-driven. Derives from `ORIGINAL_REQUEST.md` (R1-R4) independent of implementation internals.
- Methodology: Category-Partition + Boundary Value Analysis + Combinatorial Input Testing + Firmware Emulation / Static Verification.

## Feature Inventory & Test Mapping
| # | Feature | Source (Requirement) | Tier 1 (Bytecode) | Tier 2 (Symbols) | Tier 3 (Input) | Tier 4 (Sign/Pack) |
|---|---------|---------------------|:-----------------:|:----------------:|:--------------:|:------------------:|
| 1 | Dynamic HAL Probing | ORIGINAL_REQUEST §R1 | ✓ | ✓ | | |
| 2 | Defensive RGB Matrix Fallback | ORIGINAL_REQUEST §R1 | ✓ | ✓ | | |
| 3 | Defensive Neutral WB Fallback | ORIGINAL_REQUEST §R1 | ✓ | ✓ | | |
| 4 | Safe DMA Memory Reclamation | ORIGINAL_REQUEST §R1 | ✓ | ✓ | | |
| 5 | Defensive Parameter Normalization | ORIGINAL_REQUEST §R1 | ✓ | ✓ | | |
| 6 | Original WB State Protection | ORIGINAL_REQUEST §R1 | ✓ | ✓ | | |
| 7 | Multi-Dial / Dual-Dial Support | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 8 | Triple-Dial Support | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 9 | Single-Dial & D-Pad Adaptation | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 10 | RX Compact Lens Control Ring | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 11 | Touch-Only Navigation (A5100) | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 12 | Center Button Standardizing (0xe8) | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 13 | Enter5Way / Joystick Fallback | ORIGINAL_REQUEST §R2 | | | ✓ | |
| 14 | Dalvik Bytecode Verification | ORIGINAL_REQUEST §R3 | ✓ | | | |
| 15 | Dual-Compatible V1 JAR Signing | ORIGINAL_REQUEST §R3 | | | | ✓ |
| 16 | ZipAlign & Manifest Verification | ORIGINAL_REQUEST §R3 | | | | ✓ |

## Test Architecture
- **Location**: `tools/testbench/`
- **Master Test Runner**: `tools/testbench/run_testbench.py`
- **Pass/Fail Semantics**: Exits with return code 0 if all tests pass; non-zero if any test fails.
- **Tiers**:
  - **Tier 1**: `test_dalvik_verification.py` (Smali syntax, register limits, Dalvik API 10 opcode and register audit).
  - **Tier 2**: `test_pmca_symbols.py` (PMCA framework symbol compliance audit for Gen 1 & Gen 2).
  - **Tier 3**: `test_input_ergonomics.py` (Multi-model synthetic key/dial/ring/touch event stream simulation).
  - **Tier 4**: `test_apk_signing.py` (V1 JAR signature, SHA-1 digest, and Apache Harmony ASN.1 validator).
- **Directory Layout**:
  ```
  tools/testbench/
  ├── run_testbench.py
  ├── test_dalvik_verification.py
  ├── test_pmca_symbols.py
  ├── test_input_ergonomics.py
  ├── test_apk_signing.py
  └── mock_pmca_framework/
      ├── gen1_symbols.json
      └── gen2_symbols.json
  ```

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | NEX-5R / Gen 1 Legacy Camera Execution | F1, F2, F3, F5, F14, F15 | High |
| 2 | A7 Series Dual-Dial Preset Switching | F7, F8, F9, F12 | Medium |
| 3 | RX100 M4 Lens Control Ring Preset Selection | F10, F12, F1 | Medium |
| 4 | A5100 Touchscreen Filter Selection & Tap Confirm | F11, F12, F1 | Medium |
| 5 | A6000 Customized Center Key Bypass | F9, F12, F13 | High |
| 6 | Full APK Build, Sign, and Verification Lifecycle | F14, F15, F16 | High |

## Coverage Thresholds
- Tier 1: Static Dalvik verification across all modified smali files with 0 syntax errors and 0 Dalvik API 10 opcode violations.
- Tier 2: 100% audit of all CameraEx and ParameterModifier calls against Gen 1 and Gen 2 framework symbol catalogs.
- Tier 3: Pairwise simulation of all 5 hardware profiles (A7 dual-dial, A6000/6300 single-dial, RX compact lens ring, A5100 touch, custom center key).
- Tier 4: Validation of V1 JAR signature, SHA-1 digest, zipalign 4-byte boundaries, and zero CMS/V2/V3 attributes.
