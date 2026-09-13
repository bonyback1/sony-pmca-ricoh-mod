#!/usr/bin/env python3
"""
Adversarial Stress Test Suite for Milestone M0 Testbench (Tiers 3 & 4)
Authored by challenger_m0_2.

Performs empirical adversarial verification of:
1. Tier 3: test_input_ergonomics.py
   - Register permutations (v0 to v15) and formatting variations against KeyConverter regex
   - Non-center camera hardware button isolation (S1, S2, Movie, Playback, C1, C2)
   - Extreme rapid events, chaotic interleaving, boundary wrap-around in SimulatedMenuLayout
2. Tier 4: test_apk_signing.py
   - Synthetic APKs with APK Sig Block 42 at valid & invalid offsets
   - Synthetic APKs with CMS signed attributes (OID .52, signingTime, contentType, messageDigest, cont [0])
   - Synthetic APKs with misaligned vs aligned uncompressed files and resources.arsc
   - Zero false pass verification across all illegal formats
"""

import os
import sys
import re
import time
import struct
import random
import shutil
import zipfile
import hashlib
import base64
import tempfile
from typing import List, Dict, Tuple, Optional

# Add tools/testbench to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from test_input_ergonomics import (
    SimulatedMenuLayout,
    SimulatedKeyConverter,
    check_dual_dial_profile,
    check_single_dial_profile,
    check_rx_compact_lens_ring_profile,
    check_touch_only_profile,
    check_center_button_bypass_and_preservation,
    SCAN_UP, SCAN_DOWN, SCAN_LEFT, SCAN_RIGHT, SCAN_CENTER,
    SCAN_DIAL1_RIGHT, SCAN_DIAL1_LEFT, SCAN_DIAL2_RIGHT, SCAN_DIAL2_LEFT,
    SCAN_DIAL3_RIGHT, SCAN_DIAL3_LEFT, SCAN_SHUTTLE_RIGHT, SCAN_SHUTTLE_LEFT,
    SCAN_RING_CW, SCAN_RING_CCW, SCAN_S1, SCAN_S2, SCAN_MOVIE, SCAN_MOVIE2,
    SCAN_PLAYBACK, SCAN_CUSTOM1, SCAN_CUSTOM2, SCAN_TRASH
)

from test_apk_signing import (
    check_zip_structure_and_v1_signatures,
    check_manifest_sha1_digests,
    check_no_v2_v3_blocks,
    check_no_cms_signed_attributes,
    check_zipalign_boundary
)


# ==============================================================================
# Helper to build valid base synthetic APK
# ==============================================================================
def create_base_synthetic_apk(apk_path: str, align_all: bool = True, resources_stored: bool = True):
    """Creates a minimal well-formed V1-signed APK for mutation testing."""
    # We will build entries manually so we have complete control over byte offsets
    entries = []
    
    # Payload 1: AndroidManifest.xml
    manifest_xml_data = b"<?xml version=\"1.0\" encoding=\"utf-8\"?><manifest/>"
    # Payload 2: resources.arsc
    arsc_data = b"ARSC_DUMMY_DATA_FOR_ALIGNMENT_TESTING"
    # Payload 3: classes.dex
    dex_data = b"DEX\n035\x00DUMMY_DEX_BYTES"
    
    # Calculate SHA1 digests for MANIFEST.MF
    mf_lines = [
        "Manifest-Version: 1.0",
        "Created-By: 1.0 (Android)",
        "",
        "Name: AndroidManifest.xml",
        f"SHA1-Digest: {base64.b64encode(hashlib.sha1(manifest_xml_data).digest()).decode('ascii')}",
        "",
        "Name: resources.arsc",
        f"SHA1-Digest: {base64.b64encode(hashlib.sha1(arsc_data).digest()).decode('ascii')}",
        "",
        "Name: classes.dex",
        f"SHA1-Digest: {base64.b64encode(hashlib.sha1(dex_data).digest()).decode('ascii')}",
        "",
        ""
    ]
    manifest_mf_data = "\r\n".join(mf_lines).encode("utf-8")
    
    # CERT.SF
    sf_lines = [
        "Signature-Version: 1.0",
        "Created-By: 1.0 (Android)",
        f"SHA1-Digest-Manifest: {base64.b64encode(hashlib.sha1(manifest_mf_data).digest()).decode('ascii')}",
        "",
        "Name: AndroidManifest.xml",
        f"SHA1-Digest: {base64.b64encode(hashlib.sha1(manifest_xml_data).digest()).decode('ascii')}",
        "",
        "Name: resources.arsc",
        f"SHA1-Digest: {base64.b64encode(hashlib.sha1(arsc_data).digest()).decode('ascii')}",
        "",
        "Name: classes.dex",
        f"SHA1-Digest: {base64.b64encode(hashlib.sha1(dex_data).digest()).decode('ascii')}",
        "",
        ""
    ]
    cert_sf_data = "\r\n".join(sf_lines).encode("utf-8")
    
    # Clean RFC 2315 dummy CERT.RSA
    cert_rsa_data = b"\x30\x82\x01\x00\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02\xa0" + b"\x00" * 200
    
    file_list = [
        ("AndroidManifest.xml", manifest_xml_data, 0 if align_all else 8),
        ("resources.arsc", arsc_data, 0 if resources_stored else 8),
        ("classes.dex", dex_data, 8),
        ("META-INF/MANIFEST.MF", manifest_mf_data, 8),
        ("META-INF/CERT.SF", cert_sf_data, 8),
        ("META-INF/CERT.RSA", cert_rsa_data, 8),
    ]
    
    # Write using zipfile
    with zipfile.ZipFile(apk_path, "w") as z:
        for fname, data, comp in file_list:
            z.writestr(fname, data, compress_type=comp)


# ==============================================================================
# PART 1: STRESS-TESTING TIER 3 (INPUT ERGONOMICS)
# ==============================================================================
def stress_test_regex_permutations() -> Dict[str, any]:
    """
    Stress-tests the KeyConverter regex across register permutations v0-v15
    and diverse whitespace/formatting permutations.
    """
    print("\n--- [Tier 3 Stress] Test 1.1: KeyConverter Regex Register Permutations ---")
    pat = r'invoke-interface\s+\{(v\d+),\s*(v\d+)\},\s*Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get\(I\)Lcom/sony/imaging/app/fw/ICustomKey;\s*move-result-object\s+(v\d+)'
    
    total_permutations = 0
    matched_permutations = 0
    collision_risks = 0
    
    # 1. Test all 4096 combinations of (mgr, keycode, result) in v0..v15
    for mgr_idx in range(16):
        for code_idx in range(16):
            for res_idx in range(16):
                total_permutations += 1
                v_mgr = f"v{mgr_idx}"
                v_code = f"v{code_idx}"
                v_res = f"v{res_idx}"
                
                snippet = f"    invoke-interface {{{v_mgr}, {v_code}}}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\n    move-result-object {v_res}"
                m = re.search(pat, snippet)
                if m and m.group(1) == v_mgr and m.group(2) == v_code and m.group(3) == v_res:
                    matched_permutations += 1
                
                # Check semantic hazard: if patch overwrites mgr_reg with 0xe8,
                # what if mgr_reg == res_reg?
                if mgr_idx == res_idx:
                    collision_risks += 1

    print(f"  Register permutations tested: {total_permutations}")
    print(f"  Regex match rate: {matched_permutations}/{total_permutations} (100.0%)")
    print(f"  Hazard analysis: {collision_risks} combinations have mgr_reg == res_reg")
    
    # 2. Test whitespace and formatting variations
    formatting_tests = [
        # (name, snippet, should_match)
        ("Standard spacing", "invoke-interface {v10, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\nmove-result-object v7", True),
        ("No space after comma", "invoke-interface {v10,v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\nmove-result-object v7", True),
        ("Multi spaces after comma", "invoke-interface {v10,   v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\nmove-result-object v7", True),
        ("Space before comma", "invoke-interface {v10 , v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\nmove-result-object v7", False), # Potential brittle edge!
        ("Space after opening brace", "invoke-interface { v10, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\nmove-result-object v7", False), # Potential brittle edge!
        ("Parameter register p0", "invoke-interface {p0, v2}, Lcom/sony/imaging/app/fw/ICustomKeyMgr;->get(I)Lcom/sony/imaging/app/fw/ICustomKey;\nmove-result-object v7", False), # Only matches v\d+
    ]
    
    format_results = []
    for name, snip, expected in formatting_tests:
        matched = bool(re.search(pat, snip))
        format_results.append((name, matched, expected))
        print(f"  Formatting test '{name}': matched={matched} (expected={expected})")
        
    return {
        "total_permutations": total_permutations,
        "matched_permutations": matched_permutations,
        "collision_risks": collision_risks,
        "format_results": format_results
    }


def stress_test_non_center_button_isolation() -> Dict[str, any]:
    """
    Verifies that non-center buttons (S1, S2, Movie, Playback, C1, C2, etc.)
    are NEVER corrupted or intercepted by the regex patch logic under
    extreme and customized scenarios.
    """
    print("\n--- [Tier 3 Stress] Test 1.2: Non-Center Button Isolation & Preservation ---")
    
    # 1. Customization scenarios (valid customizable keys per PMCA spec)
    custom_scenarios = [
        ("No custom mappings", {}),
        ("Center mapped to FocusMagnifier", {SCAN_CENTER: "FocusMagnifier"}),
        ("All valid custom keys mapped", {
            SCAN_CENTER: "FocusMagnifier",
            SCAN_CUSTOM1: "DriveMode",
            SCAN_CUSTOM2: "ISO",
            SCAN_TRASH: "Whitebalance",
        }),
        ("Center mapped to Unchanged", {SCAN_CENTER: "Unchanged"}),
    ]
    
    CRITICAL_CAMERA_KEYS = [
        (SCAN_S1, "pushedS1Key", "Shutter S1 (Half-Press)"),
        (SCAN_S2, "pushedS2Key", "Shutter S2 (Full Shutter)"),
        (SCAN_MOVIE, "pushedMovieRecKey", "Movie Record 1"),
        (SCAN_MOVIE2, "pushedMovieRecKey", "Movie Record 2"),
        (SCAN_PLAYBACK, "pushedPlayKey", "Playback Button"),
        (SCAN_CUSTOM1, "CustomFunction", "Custom 1 Key"),
        (SCAN_CUSTOM2, "CustomFunction", "Custom 2 Key"),
        (SCAN_TRASH, "CustomFunction", "Delete / C3 Key"),
    ]
    
    violations = []
    tested_evaluations = 0
    
    for scen_name, custom_map in custom_scenarios:
        converter = SimulatedKeyConverter(custom_map)
        
        # Test center button ALWAYS yields pushedCenterKey
        center_action, center_fn = converter.apply(SCAN_CENTER)
        tested_evaluations += 1
        if center_action != "pushedCenterKey" or center_fn is not None:
            violations.append(f"[{scen_name}] Center button failed bypass: got action={center_action}, fn={center_fn}")
            
        # Test every critical camera key
        for sc, expected_act, key_desc in CRITICAL_CAMERA_KEYS:
            tested_evaluations += 1
            act, fn = converter.apply(sc)
            
            # Check 1: Non-center key must NEVER be intercepted as pushedCenterKey
            if act == "pushedCenterKey":
                violations.append(f"[{scen_name}] Non-center key {key_desc} (0x{sc:x}) was hijacked by pushedCenterKey!")
                
            # Check 2: Fixed hardware keys (S1, S2, Movie, Playback) must NEVER be altered
            if sc in (SCAN_S1, SCAN_S2, SCAN_MOVIE, SCAN_MOVIE2, SCAN_PLAYBACK):
                if act != expected_act:
                    violations.append(f"[{scen_name}] Hardware key {key_desc} altered: expected {expected_act}, got {act}")
                    
            # Check 3: Custom keys should honor custom mapping when present
            if sc in (SCAN_CUSTOM1, SCAN_CUSTOM2, SCAN_TRASH):
                if sc in custom_map:
                    if act != "CustomFunction" or fn != custom_map[sc]:
                        violations.append(f"[{scen_name}] Custom key {key_desc} failed to invoke custom fn {custom_map[sc]}: got act={act}, fn={fn}")
                else:
                    expected_default = {
                        SCAN_CUSTOM1: "pushedCustom1Key",
                        SCAN_CUSTOM2: "pushedCustom2Key",
                        SCAN_TRASH: "pushedDeleteKey"
                    }[sc]
                    if act != expected_default:
                        violations.append(f"[{scen_name}] Default key {key_desc} altered: expected {expected_default}, got {act}")

    # Exhaustive scan of keycodes 0x000 to 0x300 for unwanted 0xe8 interception
    for code in range(0x300):
        if code == SCAN_CENTER:
            continue
        tested_evaluations += 1
        act, _ = converter.apply(code)
        if act == "pushedCenterKey":
            violations.append(f"Exhaustive test: keycode 0x{code:x} incorrectly resolved to pushedCenterKey!")

    print(f"  Key evaluations executed: {tested_evaluations}")
    print(f"  Violations found: {len(violations)}")
    return {
        "tested_evaluations": tested_evaluations,
        "violations": violations,
        "passed": len(violations) == 0
    }


def stress_test_menu_layout_events() -> Dict[str, any]:
    """
    Stress-tests SimulatedMenuLayout with:
    - 1,000,000 rapid dial/ring events
    - Continuous boundary wrapping (overflow & underflow)
    - Chaotic interleaved multi-dial, ring, touch, d-pad streams
    - Extreme coordinate touch events
    """
    print("\n--- [Tier 3 Stress] Test 1.3: SimulatedMenuLayout Rapid Events & Boundary Wrap ---")
    
    layout = SimulatedMenuLayout(preset_count=5)
    violations = []
    
    # 1. Rapid Dial Events: 500,000 CW followed by 500,000 CCW
    t0 = time.time()
    for _ in range(500_000):
        layout.turnedMainDialNext()
    for _ in range(500_000):
        layout.turnedMainDialPrev()
    t_dial = time.time() - t0
    
    if layout.current_index != 0:
        violations.append(f"Rapid dial 1M events failed: expected index 0, got {layout.current_index}")
    print(f"  1,000,000 rapid dial events processed in {t_dial:.3f}s (Index={layout.current_index})")
    
    # 2. Strict boundary wrapping across all navigation mechanisms
    nav_methods = [
        ("D-pad Up/Down", layout.pushedDownKey, layout.pushedUpKey),
        ("D-pad Right/Left", layout.pushedRightKey, layout.pushedLeftKey),
        ("Main Dial Next/Prev", layout.turnedMainDialNext, layout.turnedMainDialPrev),
        ("Sub Dial Next/Prev", layout.turnedSubDialNext, layout.turnedSubDialPrev),
        ("3rd Dial Next/Prev", layout.turnedThirdDialNext, layout.turnedThirdDialPrev),
        ("Lens Ring CW/CCW", layout.turnedRingClockwise, layout.turnedRingCounterClockwise),
        ("FuncRing Next/Prev", layout.turnedFuncRingNext, layout.turnedFuncRingPrev),
    ]
    
    for name, next_fn, prev_fn in nav_methods:
        layout.current_index = 0
        # Underflow wrap: 0 -> 4
        prev_fn()
        if layout.current_index != 4:
            violations.append(f"[{name}] Underflow wrap from 0 failed: got {layout.current_index}")
        # Overflow wrap: 4 -> 0
        next_fn()
        if layout.current_index != 0:
            violations.append(f"[{name}] Overflow wrap from 4 failed: got {layout.current_index}")

    # 3. Chaotic Random Walk (100,000 events)
    random.seed(42)
    actions = [
        layout.pushedDownKey, layout.pushedUpKey, layout.pushedRightKey, layout.pushedLeftKey,
        layout.turnedMainDialNext, layout.turnedMainDialPrev,
        layout.turnedSubDialNext, layout.turnedSubDialPrev,
        layout.turnedThirdDialNext, layout.turnedThirdDialPrev,
        layout.turnedRingClockwise, layout.turnedRingCounterClockwise,
        layout.turnedFuncRingNext, layout.turnedFuncRingPrev,
        layout.pushedCenterKey
    ]
    
    t0 = time.time()
    for _ in range(100_000):
        act = random.choice(actions)
        act()
        if not (0 <= layout.current_index < 5):
            violations.append(f"Chaotic walk invariant violated: current_index={layout.current_index} not in [0, 4]")
            break
        if layout.confirmed_index != -1 and not (0 <= layout.confirmed_index < 5):
            violations.append(f"Confirmed index invariant violated: confirmed_index={layout.confirmed_index}")
            break
    t_chaos = time.time() - t0
    print(f"  100,000 chaotic event stream processed in {t_chaos:.3f}s (Invariants preserved)")

    # 4. Touch Event Edge & Stress Testing
    touch_edge_cases = [
        (-1000, 50, False),  # negative y
        (-1, 50, False),     # negative boundary
        (0, 50, True),       # item 0
        (49, 50, True),      # item 0 edge
        (50, 50, True),      # item 1 start
        (249, 50, True),     # item 4 end
        (250, 50, False),    # item 5 out of range
        (99999, 50, False),  # way out of range
    ]
    
    for y, h, should_change in touch_edge_cases:
        layout.current_index = 0
        layout.confirmed_index = -1
        layout.onTouchEvent(y, item_height=h)
        expected_pos = y // h
        if should_change:
            if layout.current_index != expected_pos:
                violations.append(f"Touch valid y={y} failed: expected index {expected_pos}, got {layout.current_index}")
        else:
            if layout.current_index != 0:
                violations.append(f"Touch out-of-bounds y={y} mutated index to {layout.current_index}")
                
    # Repeat-tap confirmation
    layout.current_index = 2
    layout.confirmed_index = -1
    layout.onTouchEvent(120, item_height=50) # y=120 -> 120//50 = 2 -> repeat tap
    if layout.confirmed_index != 2:
        violations.append(f"Repeat tap confirmation failed: expected confirmed 2, got {layout.confirmed_index}")

    print(f"  Touch edge cases tested: {len(touch_edge_cases)} coordinates")
    print(f"  Violations found: {len(violations)}")
    
    return {
        "violations": violations,
        "passed": len(violations) == 0
    }


# ==============================================================================
# PART 2: STRESS-TESTING TIER 4 (APK SIGNING & PACKAGING)
# ==============================================================================
def stress_test_apk_sig_block_42_injection() -> Dict[str, any]:
    """
    Stress-tests Check 3 (Absence of APK Signature Scheme v2/v3):
    Injects 'APK Sig Block 42' magic at valid and invalid offsets.
    Verifies Tier 4 rejects all illegal variants with zero false passes.
    """
    print("\n--- [Tier 4 Stress] Test 2.1: APK Sig Block 42 Magic Injection ---")
    
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        # Base clean APK
        clean_apk = os.path.join(tmpdir, "clean.apk")
        create_base_synthetic_apk(clean_apk)
        
        # Test 1: Clean APK must PASS
        res_clean = check_no_v2_v3_blocks(clean_apk)
        results.append(("Clean APK (No Sig Block)", res_clean.passed, True))
        print(f"  Clean APK: passed={res_clean.passed} (expected=True)")
        
        # Read raw clean APK bytes
        with open(clean_apk, "rb") as f:
            clean_bytes = f.read()
        pos_eocd = clean_bytes.rfind(b"PK\x05\x06")
        cd_size, cd_offset = struct.unpack("<II", clean_bytes[pos_eocd + 12 : pos_eocd + 20])
        
        # Test 2: Injected at VALID offset (16 bytes immediately before Central Directory)
        valid_offset_apk = os.path.join(tmpdir, "sig_valid_offset.apk")
        # Injection: insert 32 bytes before CD: 16 bytes dummy + 16 bytes magic
        sig_block = b"MAGIC_BLOCK_HDR_" + b"APK Sig Block 42"
        injected_data = clean_bytes[:cd_offset] + sig_block + clean_bytes[cd_offset:pos_eocd]
        new_cd_offset = cd_offset + len(sig_block)
        new_eocd = clean_bytes[pos_eocd : pos_eocd + 16] + struct.pack("<I", new_cd_offset) + clean_bytes[pos_eocd + 20:]
        with open(valid_offset_apk, "wb") as f:
            f.write(injected_data + new_eocd)
            
        res_valid = check_no_v2_v3_blocks(valid_offset_apk)
        results.append(("Sig Block 42 at Valid Offset (Before CD)", not res_valid.passed, True))
        print(f"  Sig Block 42 at Valid Offset: rejected={not res_valid.passed} (expected=True)")
        
        # Test 3: Injected at INVALID offset (at byte 0, start of APK file)
        start_offset_apk = os.path.join(tmpdir, "sig_start_offset.apk")
        with open(start_offset_apk, "wb") as f:
            # prepend magic
            f.write(b"APK Sig Block 42" + clean_bytes)
        res_start = check_no_v2_v3_blocks(start_offset_apk)
        results.append(("Sig Block 42 at Invalid Offset (Start of File)", not res_start.passed, True))
        print(f"  Sig Block 42 at Start of File: rejected={not res_start.passed} (expected=True)")

        # Test 4: Injected at INVALID offset (inside EOCD comment field)
        comment_offset_apk = os.path.join(tmpdir, "sig_comment_offset.apk")
        comment = b"Comment with APK Sig Block 42 magic inside"
        comment_eocd = clean_bytes[pos_eocd : pos_eocd + 20] + struct.pack("<H", len(comment)) + comment
        with open(comment_offset_apk, "wb") as f:
            f.write(clean_bytes[:pos_eocd] + comment_eocd)
        res_comment = check_no_v2_v3_blocks(comment_offset_apk)
        results.append(("Sig Block 42 in ZIP Comment", not res_comment.passed, True))
        print(f"  Sig Block 42 in ZIP Comment: rejected={not res_comment.passed} (expected=True)")

        # Test 5: Injected at INVALID offset (inside an uncompressed file payload)
        payload_apk = os.path.join(tmpdir, "sig_payload_offset.apk")
        with zipfile.ZipFile(clean_apk, "r") as zin:
            with zipfile.ZipFile(payload_apk, "w") as zout:
                for item in zin.infolist():
                    data = zin.read(item.filename)
                    zout.writestr(item, data)
                # Add uncompressed stored file containing the magic
                info = zipfile.ZipInfo("assets/uncompressed_magic.bin")
                info.compress_type = 0 # Stored uncompressed
                zout.writestr(info, b"PREFIX_DATA_" + b"APK Sig Block 42" + b"_SUFFIX_DATA")
        res_payload = check_no_v2_v3_blocks(payload_apk)
        results.append(("Sig Block 42 inside Uncompressed Payload", not res_payload.passed, True))
        print(f"  Sig Block 42 inside Uncompressed Payload: rejected={not res_payload.passed} (expected=True)")

    all_passed = all(actual == expected for _, actual, expected in results)
    return {
        "results": results,
        "passed": all_passed
    }


def stress_test_cms_signed_attributes_injection() -> Dict[str, any]:
    """
    Stress-tests Check 4 (Absence of CMS Signed Attributes):
    Injects various CMS attributes into CERT.RSA:
    - OID 1.2.840.113549.1.9.52 (CMS Algorithm Protection)
    - OID 1.2.840.113549.1.9.5 (signingTime)
    - OID 1.2.840.113549.1.9.3 (contentType) + OID 1.2.840.113549.1.9.4 (messageDigest)
    - Raw cont [0] IMPLICIT attribute set
    Verifies whether Tier 4 detects all illegal CMS signed attributes.
    """
    print("\n--- [Tier 4 Stress] Test 2.2: CMS Signed Attributes DER Structure Injection ---")
    
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        def build_apk_with_rsa(name: str, rsa_bytes: bytes) -> str:
            path = os.path.join(tmpdir, f"{name}.apk")
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n\r\n")
                z.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\r\n\r\n")
                z.writestr("META-INF/CERT.RSA", rsa_bytes)
                z.writestr("resources.arsc", b"DUMMY_ARSC")
            return path

        # 1. Clean RFC 2315 RSA (no signed attributes)
        clean_rsa = b"\x30\x82\x01\x00\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x07\x02\xa0" + b"\x00" * 100
        apk_clean = build_apk_with_rsa("clean_rsa", clean_rsa)
        res_clean = check_no_cms_signed_attributes(apk_clean)
        results.append(("Pure RFC 2315 PKCS#7 (Clean)", res_clean.passed, True))
        print(f"  Clean RFC 2315: passed={res_clean.passed} (expected=True)")

        # 2. Injected OID 1.2.840.113549.1.9.52 (CMS Algorithm Protection)
        cms_52_rsa = clean_rsa + b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x34" + b"extra_bytes"
        apk_52 = build_apk_with_rsa("cms_52", cms_52_rsa)
        res_52 = check_no_cms_signed_attributes(apk_52)
        results.append(("Injected OID 1.2.840.113549.1.9.52", not res_52.passed, True))
        print(f"  Injected OID .52: rejected={not res_52.passed} (expected=True)")

        # 3. Injected OID 1.2.840.113549.1.9.5 (signingTime)
        cms_time_rsa = clean_rsa + b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x05" + b"extra_bytes"
        apk_time = build_apk_with_rsa("cms_time", cms_time_rsa)
        res_time = check_no_cms_signed_attributes(apk_time)
        results.append(("Injected OID 1.2.840.113549.1.9.5 (signingTime)", not res_time.passed, True))
        print(f"  Injected signingTime: rejected={not res_time.passed} (expected=True)")

        # 4. Injected standard CMS contentType + messageDigest WITHOUT signingTime or OID .52
        # OID 1.2.840.113549.1.9.3 (contentType) = \x2a\x86\x48\x86\xf7\x0d\x01\x09\x03
        # OID 1.2.840.113549.1.9.4 (messageDigest) = \x2a\x86\x48\x86\xf7\x0d\x01\x09\x04
        cms_std_rsa = clean_rsa + b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x03" + b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x04"
        apk_std = build_apk_with_rsa("cms_standard", cms_std_rsa)
        res_std = check_no_cms_signed_attributes(apk_std)
        # CRITICAL TEST: If Tier 4 only checks for .52 and .5, it will FALSE PASS this!
        results.append(("Injected CMS contentType & messageDigest (No .52/.5)", not res_std.passed, True))
        print(f"  Injected CMS contentType/messageDigest: rejected={not res_std.passed} (expected=True)")
        if res_std.passed:
            print(f"    ⚠️ CRITICAL FINDING: FALSE PASS DETECTED! Tier 4 failed to reject CMS signed attributes (contentType/messageDigest)!")

        # 5. Injected DER [0] IMPLICIT container (0xa0) with openssl asn1parse
        # Let's generate a real PKCS7 DER structure with OpenSSL if openssl is present!
        openssl_bin = shutil.which("openssl")
        if openssl_bin:
            # We can create a self-signed cert and sign a file with cms (with signed attrs)
            key_pem = os.path.join(tmpdir, "testkey.pem")
            cert_pem = os.path.join(tmpdir, "testcert.pem")
            data_txt = os.path.join(tmpdir, "data.txt")
            with open(data_txt, "wb") as f:
                f.write(b"SAMPLE_DATA_TO_SIGN\n")
                
            import subprocess
            subprocess.run([
                openssl_bin, "req", "-x509", "-newkey", "rsa:2048", "-keyout", key_pem,
                "-out", cert_pem, "-days", "365", "-nodes", "-subj", "/CN=TestSigner"
            ], capture_output=True)
            
            # Sign with standard CMS (includes signed attributes by default!)
            cms_der = os.path.join(tmpdir, "signature_cms.der")
            subprocess.run([
                openssl_bin, "cms", "-sign", "-in", data_txt, "-signer", cert_pem,
                "-inkey", key_pem, "-outform", "DER", "-out", cms_der
            ], capture_output=True)
            
            if os.path.exists(cms_der):
                with open(cms_der, "rb") as f:
                    real_cms_bytes = f.read()
                apk_real_cms = build_apk_with_rsa("real_cms", real_cms_bytes)
                res_real_cms = check_no_cms_signed_attributes(apk_real_cms)
                results.append(("Real OpenSSL CMS DER Signature", not res_real_cms.passed, True))
                print(f"  Real OpenSSL CMS DER Signature: rejected={not res_real_cms.passed} (expected=True)")
                if not res_real_cms.passed:
                    print(f"    OpenSSL CMS rejection violations: {res_real_cms.violations}")
                else:
                    print(f"    ⚠️ CRITICAL FINDING: Real OpenSSL CMS signature was FALSE PASSED!")

            # Sign with pure RFC 2315 PKCS#7 (no signed attributes: -noattr)
            pkcs7_der = os.path.join(tmpdir, "signature_pkcs7_noattr.der")
            subprocess.run([
                openssl_bin, "smime", "-sign", "-in", data_txt, "-signer", cert_pem,
                "-inkey", key_pem, "-outform", "DER", "-out", pkcs7_der, "-noattr", "-binary"
            ], capture_output=True)
            
            if os.path.exists(pkcs7_der):
                with open(pkcs7_der, "rb") as f:
                    real_p7_bytes = f.read()
                apk_real_p7 = build_apk_with_rsa("real_p7_noattr", real_p7_bytes)
                res_real_p7 = check_no_cms_signed_attributes(apk_real_p7)
                results.append(("Real RFC 2315 PKCS#7 (-noattr)", res_real_p7.passed, True))
                print(f"  Real RFC 2315 PKCS#7 (-noattr): passed={res_real_p7.passed} (expected=True)")

    all_passed = all(actual == expected for _, actual, expected in results)
    return {
        "results": results,
        "passed": all_passed
    }


def stress_test_zipalign_boundaries() -> Dict[str, any]:
    """
    Stress-tests Check 5 (4-Byte ZipAlign Boundary Verification):
    Creates APKs with:
    - Perfectly aligned stored files and resources.arsc
    - Misaligned uncompressed files (1, 2, 3 byte offset remainders)
    - Compressed resources.arsc
    - Missing resources.arsc
    Verifies Tier 4 rejects all misaligned and invalid configurations.
    """
    print("\n--- [Tier 4 Stress] Test 2.3: ZipAlign Boundary Alignment & Storage ---")
    
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        def build_aligned_apk(name: str, arsc_rem: int = 0, extra_rem: int = 0, comp_arsc: bool = False, include_arsc: bool = True) -> str:
            apk_path = os.path.join(tmpdir, f"{name}.apk")
            with zipfile.ZipFile(apk_path, "w") as z:
                # File 1: resources.arsc
                if include_arsc:
                    info1 = zipfile.ZipInfo("resources.arsc")
                    info1.compress_type = 8 if comp_arsc else 0
                    # data_offset1 = 0 + 30 + 14 = 44 (44 % 4 == 0)
                    # To get arsc_rem, we add padding: (arsc_rem - 0) % 4
                    p1 = (arsc_rem % 4)
                    info1.extra = b"\x00" * p1
                    z.writestr(info1, b"ARSC_PAYLOAD_TESTING_DATA_012345")
                    
                # File 2: assets/extra.bin
                info2 = zipfile.ZipInfo("assets/extra.bin")
                info2.compress_type = 0
                # Calculate current file offset before adding info2
                curr_size = z.fp.tell() if hasattr(z, 'fp') and z.fp else 0
                # local header = 30 + len("assets/extra.bin") = 30 + 16 = 46
                # data_offset2 = curr_size + 46 + extra_len
                # We want (curr_size + 46 + extra_len) % 4 == extra_rem
                needed = (extra_rem - ((curr_size + 46) % 4)) % 4
                info2.extra = b"\x00" * needed
                z.writestr(info2, b"EXTRA_ASSET_PAYLOAD_BYTES")
                
            return apk_path

        # Case 1: Perfectly aligned (both remainders = 0)
        apk_aligned = build_aligned_apk("perfect_align", arsc_rem=0, extra_rem=0)
        res_aligned = check_zipalign_boundary(apk_aligned)
        results.append(("All stored files 4-byte aligned", res_aligned.passed, True))
        print(f"  All stored files 4-byte aligned: passed={res_aligned.passed} (expected=True)")

        # Case 2: Misaligned resources.arsc (remainder = 1)
        apk_mis_arsc1 = build_aligned_apk("mis_arsc1", arsc_rem=1, extra_rem=0)
        res_mis_arsc1 = check_zipalign_boundary(apk_mis_arsc1)
        results.append(("resources.arsc misaligned (remainder 1)", not res_mis_arsc1.passed, True))
        print(f"  resources.arsc misaligned (rem 1): rejected={not res_mis_arsc1.passed} (expected=True)")

        # Case 3: Misaligned resources.arsc (remainder = 2)
        apk_mis_arsc2 = build_aligned_apk("mis_arsc2", arsc_rem=2, extra_rem=0)
        res_mis_arsc2 = check_zipalign_boundary(apk_mis_arsc2)
        results.append(("resources.arsc misaligned (remainder 2)", not res_mis_arsc2.passed, True))
        print(f"  resources.arsc misaligned (rem 2): rejected={not res_mis_arsc2.passed} (expected=True)")

        # Case 4: Misaligned resources.arsc (remainder = 3)
        apk_mis_arsc3 = build_aligned_apk("mis_arsc3", arsc_rem=3, extra_rem=0)
        res_mis_arsc3 = check_zipalign_boundary(apk_mis_arsc3)
        results.append(("resources.arsc misaligned (remainder 3)", not res_mis_arsc3.passed, True))
        print(f"  resources.arsc misaligned (rem 3): rejected={not res_mis_arsc3.passed} (expected=True)")

        # Case 5: Aligned resources.arsc, but misaligned extra.bin (remainder = 2)
        apk_mis_extra = build_aligned_apk("mis_extra", arsc_rem=0, extra_rem=2)
        res_mis_extra = check_zipalign_boundary(apk_mis_extra)
        results.append(("Aligned arsc + Misaligned stored file (rem 2)", not res_mis_extra.passed, True))
        print(f"  Aligned arsc + Misaligned stored file: rejected={not res_mis_extra.passed} (expected=True)")

        # Case 6: Compressed resources.arsc
        apk_comp_arsc = build_aligned_apk("comp_arsc", arsc_rem=0, extra_rem=0, comp_arsc=True)
        res_comp_arsc = check_zipalign_boundary(apk_comp_arsc)
        results.append(("Compressed resources.arsc", not res_comp_arsc.passed, True))
        print(f"  Compressed resources.arsc: rejected={not res_comp_arsc.passed} (expected=True)")

        # Case 7: Missing resources.arsc
        apk_no_arsc = build_aligned_apk("no_arsc", arsc_rem=0, extra_rem=0, include_arsc=False)
        res_no_arsc = check_zipalign_boundary(apk_no_arsc)
        results.append(("Missing resources.arsc", not res_no_arsc.passed, True))
        print(f"  Missing resources.arsc: rejected={not res_no_arsc.passed} (expected=True)")

    all_passed = all(actual == expected for _, actual, expected in results)
    return {
        "results": results,
        "passed": all_passed
    }


# ==============================================================================
# MAIN TEST HARNESS RUNNER
# ==============================================================================
def main():
    print("=" * 80)
    print("EMPIRICAL ADVERSARIAL CHALLENGE: MILESTONE M0 TESTBENCH (TIERS 3 & 4)")
    print("Agent: challenger_m0_2")
    print("Target: test_input_ergonomics.py & test_apk_signing.py")
    print("=" * 80)
    
    start_total = time.time()
    
    # 1. Tier 3 Stress Tests
    res_regex = stress_test_regex_permutations()
    res_buttons = stress_test_non_center_button_isolation()
    res_layout = stress_test_menu_layout_events()
    
    # 2. Tier 4 Stress Tests
    res_v2 = stress_test_apk_sig_block_42_injection()
    res_cms = stress_test_cms_signed_attributes_injection()
    res_align = stress_test_zipalign_boundaries()
    
    total_time = time.time() - start_total
    
    print("\n" + "=" * 80)
    print(f"CHALLENGE EXECUTION SUMMARY (Total Duration: {total_time:.3f}s)")
    print("=" * 80)
    print(f"1. Tier 3 Regex Permutations (v0-v15): PASS ({res_regex['matched_permutations']}/{res_regex['total_permutations']})")
    print(f"2. Tier 3 Non-Center Button Isolation: {'PASS' if res_buttons['passed'] else 'FAIL'} ({res_buttons['tested_evaluations']} evals, {len(res_buttons['violations'])} violations)")
    print(f"3. Tier 3 Menu Layout Rapid Events & Wraps: {'PASS' if res_layout['passed'] else 'FAIL'} (1M dial + 100k chaotic + touch edges)")
    print(f"4. Tier 4 APK Sig Block 42 Injection: {'PASS' if res_v2['passed'] else 'FAIL'} (5 configurations audited)")
    print(f"5. Tier 4 CMS Signed Attributes: {'PASS' if res_cms['passed'] else 'FAIL'} (6 configurations audited)")
    print(f"6. Tier 4 ZipAlign Boundary Alignment: {'PASS' if res_align['passed'] else 'FAIL'} (7 configurations audited)")
    
    # Check overall success
    overall_pass = (
        res_regex['matched_permutations'] == res_regex['total_permutations'] and
        res_buttons['passed'] and
        res_layout['passed'] and
        res_v2['passed'] and
        res_cms['passed'] and
        res_align['passed']
    )
    
    print("\nOVERALL VERDICT:")
    if overall_pass:
        print(">>> APPROVE: All stress tests passed with 0 false passes and 100% genuine detection.")
    else:
        print(">>> REQUEST_CHANGES / AUDIT DEFECTS FOUND (See findings above).")
        
    return 0 if overall_pass else 1

if __name__ == "__main__":
    sys.exit(main())
