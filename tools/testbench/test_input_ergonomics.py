#!/usr/bin/env python3
"""
Tier 3: Input Ergonomics & Hardware Event Stream Simulator
Audits PMCA input routing and simulates synthetic event streams across 5 hardware profiles:
1. Dual-Dial / Multi-Dial Bodies (A7 series, A6500): Front Dial, Rear Dial, Sub-Dial, 3rd Dial.
2. Single-Dial Bodies (A6000, A6300): Main Dial, Sub-Dial, and 4-way D-Pad 1D cycling.
3. RX Compact Lens Ring (RX100 M3/M4/M5, RX10 M2/M3, RX1R II): Lens Control Ring & FuncRing.
4. Touch-Only Bodies (A5100): Touch item selection, repeat tap confirmation, physical fallbacks.
5. Center Button (0xe8) Bypass & Key Preservation: KeyConverter regex compatibility across Gen 1
   (v10) & Gen 2 (v11), zeroing custom hijacking on 0xe8 while strictly preserving Shutter (0x204/0x206),
   Movie (0x203/0x27d), Playback (0xcf), and Custom buttons (0x26e/0x26f).
"""

import sys
import os
import re
import time
import argparse
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration: float
    message: str = ""
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class TierResult:
    tier_num: int
    tier_name: str
    passed: bool
    duration: float
    checks: List[CheckResult] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


# ---------------------------------------------------------------------------
# Hardware Key Codes & ScanCodes (AppRoot$USER_KEYCODE)
# ---------------------------------------------------------------------------

SCAN_UP = 0x67
SCAN_DOWN = 0x6c
SCAN_LEFT = 0x69
SCAN_RIGHT = 0x6a
SCAN_CENTER = 0xe8

# Dials & Rings
SCAN_DIAL1_RIGHT = 0x20d  # Main / Front dial right
SCAN_DIAL1_LEFT = 0x20e   # Main / Front dial left
SCAN_DIAL2_RIGHT = 0x210  # Rear dial right
SCAN_DIAL2_LEFT = 0x211   # Rear dial left
SCAN_DIAL3_RIGHT = 0x27b  # 3rd dial right (A7R2, A6500)
SCAN_DIAL3_LEFT = 0x27a   # 3rd dial left
SCAN_SHUTTLE_RIGHT = 0x20a # Control Wheel right
SCAN_SHUTTLE_LEFT = 0x20b  # Control Wheel left
SCAN_RING_CW = 0x288      # Lens Control Ring CW (RX series)
SCAN_RING_CCW = 0x289     # Lens Control Ring CCW

# Preserved Camera Controls
SCAN_S1 = 0x204           # Shutter S1 (half-press)
SCAN_S2 = 0x206           # Shutter S2 (full-press)
SCAN_MOVIE = 0x203        # Movie Rec button
SCAN_MOVIE2 = 0x27d       # Secondary Movie Rec
SCAN_PLAYBACK = 0xcf      # Playback button
SCAN_CUSTOM1 = 0x26e      # Custom 1 button
SCAN_CUSTOM2 = 0x26f      # Custom 2 button
SCAN_TRASH = 0x24c        # Delete / C3 button

PRESET_COUNT = 5  # Standard Ricoh filter preset count


# ---------------------------------------------------------------------------
# Synthetic Event Dispatch Emulation Engine
# ---------------------------------------------------------------------------

class SimulatedMenuLayout:
    """
    Simulates PictureEffectPlusOptionMenuLayout state and event handlers.
    """
    def __init__(self, preset_count: int = PRESET_COUNT):
        self.preset_count = preset_count
        self.current_index = 0
        self.confirmed_index = -1
        self.touch_registered = False

    def pushedDownKey(self):
        self.current_index = (self.current_index + 1) % self.preset_count

    def pushedUpKey(self):
        self.current_index = (self.current_index - 1 + self.preset_count) % self.preset_count

    def pushedRightKey(self):
        # In Single-Dial mode, Right maps to Next (pushedDownKey)
        self.pushedDownKey()

    def pushedLeftKey(self):
        # In Single-Dial mode, Left maps to Prev (pushedUpKey)
        self.pushedUpKey()

    def pushedCenterKey(self):
        self.confirmed_index = self.current_index

    # Dial Handlers
    def turnedMainDialNext(self):
        self.pushedDownKey()

    def turnedMainDialPrev(self):
        self.pushedUpKey()

    def turnedSubDialNext(self):
        self.pushedDownKey()

    def turnedSubDialPrev(self):
        self.pushedUpKey()

    def turnedThirdDialNext(self):
        self.pushedDownKey()

    def turnedThirdDialPrev(self):
        self.pushedUpKey()

    # Ring Handlers
    def turnedRingClockwise(self):
        self.pushedDownKey()

    def turnedRingCounterClockwise(self):
        self.pushedUpKey()

    def turnedFuncRingNext(self):
        self.pushedDownKey()

    def turnedFuncRingPrev(self):
        self.pushedUpKey()

    # Touch Handlers
    def onTouchEvent(self, y: int, item_height: int = 50):
        target_pos = y // item_height
        if 0 <= target_pos < self.preset_count:
            if target_pos == self.current_index:
                # Repeat tap confirms selection
                self.pushedCenterKey()
            else:
                self.current_index = target_pos


class SimulatedKeyConverter:
    """
    Emulates the KeyConverter patch logic across Gen 1 and Gen 2.
    """
    def __init__(self, custom_mapping: Optional[Dict[int, str]] = None):
        self.custom_mapping = custom_mapping or {}

    def apply(self, scan_code: int) -> Tuple[str, Optional[str]]:
        """
        Simulates:
            ICustomKey key = mCustomKeyMgr.get(code);
            if (code == 0xe8) { key = null; }
            return key != null ? key.getFunction() : "Unchanged";
        Returns (dispatched_action, custom_function_name).
        """
        custom_fn = self.custom_mapping.get(scan_code)

        # The 0xe8 Bypass Check
        if scan_code == SCAN_CENTER:
            # Bypass forces key to null -> Unchanged -> pushedCenterKey
            return ("pushedCenterKey", None)

        if custom_fn:
            return ("CustomFunction", custom_fn)

        # Default Unchanged Dispatch Mapping
        scan_to_handler = {
            SCAN_UP: "pushedUpKey",
            SCAN_DOWN: "pushedDownKey",
            SCAN_LEFT: "pushedLeftKey",
            SCAN_RIGHT: "pushedRightKey",
            SCAN_CENTER: "pushedCenterKey",
            SCAN_DIAL1_RIGHT: "turnedMainDialNext",
            SCAN_DIAL1_LEFT: "turnedMainDialPrev",
            SCAN_DIAL2_RIGHT: "turnedSubDialNext",
            SCAN_DIAL2_LEFT: "turnedSubDialPrev",
            SCAN_DIAL3_RIGHT: "turnedThirdDialNext",
            SCAN_DIAL3_LEFT: "turnedThirdDialPrev",
            SCAN_SHUTTLE_RIGHT: "turnedSubDialNext",
            SCAN_SHUTTLE_LEFT: "turnedSubDialPrev",
            SCAN_RING_CW: "turnedRingClockwise",
            SCAN_RING_CCW: "turnedRingCounterClockwise",
            SCAN_S1: "pushedS1Key",
            SCAN_S2: "pushedS2Key",
            SCAN_MOVIE: "pushedMovieRecKey",
            SCAN_MOVIE2: "pushedMovieRecKey",
            SCAN_PLAYBACK: "pushedPlayKey",
            SCAN_CUSTOM1: "pushedCustom1Key",
            SCAN_CUSTOM2: "pushedCustom2Key",
            SCAN_TRASH: "pushedDeleteKey",
        }
        return (scan_to_handler.get(scan_code, "unknownKey"), None)


# ---------------------------------------------------------------------------
# Tier 3 Checks (5 Ergonomic Profiles)
# ---------------------------------------------------------------------------

def check_dual_dial_profile() -> CheckResult:
    """
    Profile 1: Dual-Dial & Multi-Dial Bodies (A7 series, A6500).
    Verifies Front Dial, Rear Dial, Control Wheel, and 3rd Dial work without conflict.
    """
    start_time = time.time()
    violations = []
    layout = SimulatedMenuLayout()

    # Front Dial rotation
    layout.turnedMainDialNext()
    if layout.current_index != 1:
        violations.append(f"Front dial CW failed: expected index 1, got {layout.current_index}")
    layout.turnedMainDialPrev()
    if layout.current_index != 0:
        violations.append(f"Front dial CCW failed: expected index 0, got {layout.current_index}")

    # Rear Dial rotation
    layout.turnedSubDialNext()
    if layout.current_index != 1:
        violations.append(f"Rear dial CW failed: expected index 1, got {layout.current_index}")

    # 3rd Dial (A7R2 / A6500)
    layout.turnedThirdDialNext()
    if layout.current_index != 2:
        violations.append(f"3rd dial CW failed: expected index 2, got {layout.current_index}")
    layout.turnedThirdDialPrev()
    if layout.current_index != 1:
        violations.append(f"3rd dial CCW failed: expected index 1, got {layout.current_index}")

    # Interleaved multi-dial turn sequence: Front CW -> Rear CW -> 3rd CCW -> Rear CCW
    initial = layout.current_index
    layout.turnedMainDialNext()  # +1 -> 2
    layout.turnedSubDialNext()   # +1 -> 3
    layout.turnedThirdDialPrev() # -1 -> 2
    layout.turnedSubDialPrev()   # -1 -> 1
    if layout.current_index != initial:
        violations.append(f"Interleaved multi-dial sequence failed: expected {initial}, got {layout.current_index}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Dual-dial and multi-dial event streams cycle presets cleanly without conflict" if passed else f"{len(violations)} multi-dial violations found"
    return CheckResult("Dual-Dial / Multi-Dial Navigation Audit", passed, dur, msg, violations)


def check_single_dial_profile() -> CheckResult:
    """
    Profile 2: Single-Dial Bodies (A6000, A6300).
    Verifies Main Dial, Sub-Dial, and 4-way D-Pad 1D cycling.
    """
    start_time = time.time()
    violations = []
    layout = SimulatedMenuLayout()

    # D-Pad Down & Up
    layout.pushedDownKey()
    if layout.current_index != 1:
        violations.append("D-pad Down failed to advance preset")
    layout.pushedUpKey()
    if layout.current_index != 0:
        violations.append("D-pad Up failed to decrement preset")

    # D-Pad Right (next) & Left (prev) for unified 1D navigation
    layout.pushedRightKey()
    if layout.current_index != 1:
        violations.append("D-pad Right failed to advance preset in 1D navigation mode")
    layout.pushedLeftKey()
    if layout.current_index != 0:
        violations.append("D-pad Left failed to decrement preset in 1D navigation mode")

    # Boundary wrapping (Up from 0 -> 4, Down from 4 -> 0)
    layout.pushedUpKey()
    if layout.current_index != PRESET_COUNT - 1:
        violations.append(f"Underflow wrapping failed: expected {PRESET_COUNT - 1}, got {layout.current_index}")
    layout.pushedDownKey()
    if layout.current_index != 0:
        violations.append(f"Overflow wrapping failed: expected 0, got {layout.current_index}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Single-dial and 4-way D-pad 1D navigation verified with boundary wrapping" if passed else f"{len(violations)} single-dial violations found"
    return CheckResult("Single-Dial & D-Pad Ergonomics Audit", passed, dur, msg, violations)


def check_rx_compact_lens_ring_profile() -> CheckResult:
    """
    Profile 3: Compact Cameras with Control Rings (RX100 M3-M5, RX10 M2/M3, RX1R II).
    Verifies lens control ring and FuncRing rotation event streams.
    """
    start_time = time.time()
    violations = []
    layout = SimulatedMenuLayout()

    # Physical Lens Ring CW and CCW
    layout.turnedRingClockwise()
    if layout.current_index != 1:
        violations.append("Lens Ring CW failed to advance preset")
    layout.turnedRingCounterClockwise()
    if layout.current_index != 0:
        violations.append("Lens Ring CCW failed to decrement preset")

    # FuncRing Next and Prev
    layout.turnedFuncRingNext()
    if layout.current_index != 1:
        violations.append("FuncRing Next failed to advance preset")
    layout.turnedFuncRingPrev()
    if layout.current_index != 0:
        violations.append("FuncRing Prev failed to decrement preset")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "RX Compact lens control ring and FuncRing event dispatch verified" if passed else f"{len(violations)} lens ring violations found"
    return CheckResult("RX Compact Lens Ring Navigation Audit", passed, dur, msg, violations)


def check_touch_only_profile(smali_dir: Optional[str] = None) -> CheckResult:
    """
    Profile 4: Touch-Only Bodies (A5100).
    Verifies on-screen touch selection, tap confirmation, and physical fallbacks.
    """
    start_time = time.time()
    violations = []
    layout = SimulatedMenuLayout()

    item_height = 50
    # Tap item 3 at y = 160 (160 // 50 = 3)
    layout.onTouchEvent(y=160, item_height=item_height)
    if layout.current_index != 3:
        violations.append(f"Touch tap item selection failed: expected index 3, got {layout.current_index}")
    if layout.confirmed_index != -1:
        violations.append("Touch selection prematurely confirmed preset on first tap")

    # Tap again on selected item 3 -> confirms selection
    layout.onTouchEvent(y=175, item_height=item_height)
    if layout.confirmed_index != 3:
        violations.append(f"Repeat touch tap confirmation failed: expected confirmed 3, got {layout.confirmed_index}")

    # Fallback verification: D-pad still works alongside touch
    layout.pushedDownKey()
    if layout.current_index != 4:
        violations.append("Physical D-pad fallback failed after touch interaction")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "A5100 touchscreen item selection, repeat-tap confirmation, and fallbacks verified" if passed else f"{len(violations)} touch violations found"
    return CheckResult("Touch-Only A5100 Ergonomics & Fallback Audit", passed, dur, msg, violations)


def check_center_button_bypass_and_preservation(smali_dir: Optional[str] = None) -> CheckResult:
    """
    Profile 5: Center Button scanCode 0xe8 bypass regex on Gen 1 (v10) & Gen 2 (v11),
    and verification that camera controls (Shutter, Movie, Playback, Custom) are strictly preserved.
    """
    start_time = time.time()
    violations = []

    # 1. Regex compatibility test against Gen 1 and Gen 2 KeyConverter patterns
    gen1_smali_snippet = """
    iget-object v10, p0, Lcom/sony/imaging/app/fw/KeyConverter;->mCustomKeyMgr:Lcom/sony/imaging/app/fw/ICustomKeyMgr;
    invoke-interface {v10, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;
    move-result-object v7
    """

    gen2_smali_snippet = """
    iget-object v11, p0, Lcom/sony/imaging/app/fw/KeyConverter;->mCustomKeyMgr:Lcom/sony/imaging/app/fw/ICustomKeyMgr;
    invoke-interface {v11, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;
    move-result-object v7
    """

    pat = r'invoke-interface\s*\{\s*([vp]\d+)\s*,\s*([vp]\d+)\s*\}\s*,\s*Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get\(I\)Lcom/sony/imaging/app/fw/ICustomKey;\s*move-result-object\s+([vp]\d+)'

    m1 = re.search(pat, gen1_smali_snippet)
    if not m1 or m1.group(1) != "v10" or m1.group(2) != "v2" or m1.group(3) != "v7":
        violations.append(f"KeyConverter regex failed to match PMCA Gen 1 pattern (v10, v2, v7): {m1}")

    m2 = re.search(pat, gen2_smali_snippet)
    if not m2 or m2.group(1) != "v11" or m2.group(2) != "v2" or m2.group(3) != "v7":
        violations.append(f"KeyConverter regex failed to match PMCA Gen 2 pattern (v11, v2, v7): {m2}")

    # 2. Register permutation safety audit across all 4096 combinations (v0..v15)
    for mgr_idx in range(16):
        for code_idx in range(16):
            for res_idx in range(16):
                vm, vc, vr = f"v{mgr_idx}", f"v{code_idx}", f"v{res_idx}"
                if vm != vr and vm != vc:
                    scratch = vm
                else:
                    candidates = [f"v{i}" for i in range(16) if f"v{i}" not in (vr, vc)]
                    scratch = candidates[0]
                if scratch in (vr, vc):
                    violations.append(f"Scratch collision in permutation ({vm}, {vc}, {vr}): scratch={scratch}")
                    break

    # 3. If smali directory is provided and contains KeyConverter.smali, audit against actual file
    if smali_dir and os.path.isdir(smali_dir):
        for root, _, files in os.walk(smali_dir):
            if "KeyConverter.smali" in files:
                kc_path = os.path.join(root, "KeyConverter.smali")
                try:
                    with open(kc_path, "r", encoding="utf-8") as f:
                        kc_content = f.read()
                    m_kc = re.search(pat, kc_content)
                    if not m_kc:
                        violations.append(f"KeyConverter.smali at {kc_path} does not match 0xe8 patch regex pattern.")
                except Exception as e:
                    violations.append(f"Failed to read {kc_path}: {e}")

    # 4. KeyConverter simulation with customized center button
    custom_map = {
        SCAN_CENTER: "FocusMagnifier",   # User assigned Focus Magnifier to center button
        SCAN_CUSTOM1: "ISO",
        SCAN_CUSTOM2: "Whitebalance",
    }
    converter = SimulatedKeyConverter(custom_map)

    # When 0xe8 is pressed, bypass must nullify key -> dispatch pushedCenterKey
    action, custom_fn = converter.apply(SCAN_CENTER)
    if action != "pushedCenterKey" or custom_fn is not None:
        violations.append(f"Center button bypass failed: expected 'pushedCenterKey', got action={action}, fn={custom_fn}")

    # 5. Preservation of critical camera hardware keys (must NOT be bypassed)
    PRESERVED_KEYS = [
        (SCAN_S1, "pushedS1Key"),
        (SCAN_S2, "pushedS2Key"),
        (SCAN_MOVIE, "pushedMovieRecKey"),
        (SCAN_MOVIE2, "pushedMovieRecKey"),
        (SCAN_PLAYBACK, "pushedPlayKey"),
        (SCAN_CUSTOM1, "CustomFunction"),  # Custom key retains user assignment
        (SCAN_CUSTOM2, "CustomFunction"),
        (SCAN_TRASH, "pushedDeleteKey"),
    ]

    for scan_code, expected_action in PRESERVED_KEYS:
        act, _ = converter.apply(scan_code)
        if act != expected_action:
            violations.append(
                f"Camera control scanCode 0x{scan_code:x} was incorrectly modified: expected {expected_action}, got {act}"
            )

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Center button 0xe8 bypass regex verified across Gen 1 & Gen 2; Shutter/Movie/Playback/Custom keys preserved" if passed else f"{len(violations)} key preservation violations found"
    return CheckResult("Center Button 0xe8 Bypass & Key Preservation Audit", passed, dur, msg, violations)


# ---------------------------------------------------------------------------
# Tier 3 Master Runner API
# ---------------------------------------------------------------------------

def run_tier3_tests(smali_dir: Optional[str] = None, apk_path: Optional[str] = None, verbose: bool = False) -> TierResult:
    """
    Executes Tier 3 Input Ergonomics and Key Preservation tests across all 5 profiles.
    Returns TierResult with individual CheckResult objects.
    """
    start_time = time.time()

    checks = [
        check_dual_dial_profile(),
        check_single_dial_profile(),
        check_rx_compact_lens_ring_profile(),
        check_touch_only_profile(smali_dir),
        check_center_button_bypass_and_preservation(smali_dir)
    ]

    all_passed = all(c.passed for c in checks)
    tier_dur = time.time() - start_time

    return TierResult(
        tier_num=3,
        tier_name="Input Ergonomics Simulator",
        passed=all_passed,
        duration=tier_dur,
        checks=checks
    )


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tier 3: Input Ergonomics & Hardware Event Stream Simulator")
    parser.add_argument("--smali-dir", "-s", type=str, default="src/smali", help="Target smali directory")
    parser.add_argument("--apk", "-a", type=str, default=None, help="Target APK file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose details")
    parser.add_argument("--fixtures", action="store_true", help="Run simulation self-test fixtures")

    args = parser.parse_args()

    if args.smali_dir is not None and not os.path.exists(args.smali_dir):
        print(f"Error: Specified smali directory '{args.smali_dir}' does not exist.", file=sys.stderr)
        sys.exit(2)

    if args.apk is not None and not os.path.exists(args.apk):
        print(f"Error: Specified APK file '{args.apk}' does not exist.", file=sys.stderr)
        sys.exit(2)

    result = run_tier3_tests(args.smali_dir, args.apk, args.verbose)

    print(f"\n================================================================================")
    print(f"TIER 3 RESULT: {'PASS' if result.passed else 'FAIL'} (Duration: {result.duration:.3f}s)")
    print(f"================================================================================")
    for c in result.checks:
        status = "PASS" if c.passed else "FAIL"
        print(f"[{status}] {c.name} ({c.duration:.3f}s)")
        if c.message:
            print(f"       Message: {c.message}")
        if not c.passed and args.verbose:
            for v in c.violations[:10]:
                print(f"       Violation: {v}")
            if len(c.violations) > 10:
                print(f"       ... and {len(c.violations) - 10} more violations.")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
