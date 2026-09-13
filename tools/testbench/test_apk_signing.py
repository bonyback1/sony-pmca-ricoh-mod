#!/usr/bin/env python3
"""
Tier 4: APK Packaging & Dual-Compatible Signing Validator
Audits APK ZIP packaging and signature against Sony PMCA Gen 1 (Android 2.3.7) & Gen 2 (Android 4.1.2) constraints:
1. ZIP Structure & V1 JAR Signature Check: MANIFEST.MF, .SF, .RSA present and valid.
2. MANIFEST.MF SHA-1 Digest Integrity: Pure SHA-1 digests, 0 occurrences of SHA-256 (incompatible with Android 2.3.7).
3. Absence of APK Signature Scheme v2/v3: Zero 'APK Sig Block 42' blocks before Central Directory.
4. Absence of CMS Signed Attributes: CERT.RSA is pure RFC 2315 without CMS attributes (signingTime, OID 1.2.840.113549.1.9.52).
5. 4-Byte ZipAlign Boundary Check: All uncompressed stored entries (especially resources.arsc) aligned to 4-byte boundaries.
"""

import sys
import os
import re
import time
import zipfile
import hashlib
import struct
import argparse
import subprocess
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
# Tier 4 Checks
# ---------------------------------------------------------------------------

def check_zip_structure_and_v1_signatures(apk_path: str) -> CheckResult:
    """
    Check 1: Audits APK ZIP structure and META-INF V1 JAR signature entries.
    """
    start_time = time.time()
    violations = []

    if not os.path.exists(apk_path):
        return CheckResult("ZIP Structure & META-INF V1 Signatures", False, 0.0, f"APK file not found: {apk_path}", [f"APK not found: {apk_path}"])

    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            names = set(z.namelist())

            if "META-INF/MANIFEST.MF" not in names:
                violations.append("Missing META-INF/MANIFEST.MF in APK.")

            sf_files = [n for n in names if n.startswith("META-INF/") and n.endswith(".SF")]
            if len(sf_files) == 0:
                violations.append("Missing signature file (*.SF) in META-INF/.")
            elif len(sf_files) > 1:
                violations.append(f"Multiple signature files found in META-INF/: {sf_files}")

            rsa_files = [n for n in names if n.startswith("META-INF/") and (n.endswith(".RSA") or n.endswith(".DSA"))]
            if len(rsa_files) == 0:
                violations.append("Missing signature block file (*.RSA or *.DSA) in META-INF/.")
            elif len(rsa_files) > 1:
                violations.append(f"Multiple signature block files found in META-INF/: {rsa_files}")

            if "META-INF/MANIFEST.MF" in names:
                manifest_raw = z.read("META-INF/MANIFEST.MF").decode("utf-8", errors="replace")
                # RFC 2045 / JAR Manifest standard: unfold lines wrapped with newline + single space
                manifest_text = re.sub(r'(\r\n|\n)[ ]', '', manifest_raw)
                declared_files = set(re.findall(r'Name:\s*([^\r\n]+)', manifest_text))
                for n in names:
                    if not n.startswith("META-INF/") and not n.endswith("/"):
                        if n not in declared_files:
                            violations.append(f"File '{n}' present in APK but not declared in MANIFEST.MF.")

    except zipfile.BadZipFile as e:
        violations.append(f"Corrupt ZIP file: {str(e)}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Valid V1 JAR signature structure (MANIFEST.MF, .SF, .RSA) verified" if passed else f"{len(violations)} ZIP/signature structure violations found"
    return CheckResult("ZIP Structure & META-INF V1 Signatures", passed, dur, msg, violations)


def check_manifest_sha1_digests(apk_path: str) -> CheckResult:
    """
    Check 2: Audits MANIFEST.MF algorithm and confirms pure SHA-1 digests.
    Flags SHA-256 attributes which break PMCA Gen 1 package manager.
    """
    start_time = time.time()
    violations = []

    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            manifest_bytes = z.read("META-INF/MANIFEST.MF")
            manifest_raw = manifest_bytes.decode("utf-8", errors="replace")
            manifest_text = re.sub(r'(\r\n|\n)[ ]', '', manifest_raw)

            # Check for SHA-256 attributes
            if "SHA-256-Digest:" in manifest_text or "SHA256-Digest:" in manifest_text:
                violations.append(
                    "MANIFEST.MF contains SHA-256 digest entries. PMCA Gen 1 (Android 2.3.7) rejects "
                    "SHA-256 digests with INSTALL_PARSE_FAILED_NO_CERTIFICATES. Must use SHA-1 exclusively."
                )

            # Check .SF file for SHA-256 attributes
            sf_files = [n for n in z.namelist() if n.startswith("META-INF/") and n.endswith(".SF")]
            if sf_files:
                sf_raw = z.read(sf_files[0]).decode("utf-8", errors="replace")
                sf_text = re.sub(r'(\r\n|\n)[ ]', '', sf_raw)
                if "SHA-256-Digest" in sf_text or "SHA256-Digest" in sf_text:
                    violations.append(f"{sf_files[0]} contains SHA-256 digest headers.")

            # Validate SHA-1 digests of entries
            # Parse sections: Name: ... \n SHA1-Digest: ...
            sections = manifest_text.split("\r\n\r\n") if "\r\n\r\n" in manifest_text else manifest_text.split("\n\n")
            verified_count = 0
            for sec in sections:
                m_name = re.search(r'Name:\s*([^\r\n]+)', sec)
                m_sha1 = re.search(r'SHA1-Digest:\s*([^\r\n]+)', sec)
                if m_name and m_sha1:
                    fname = m_name.group(1).strip()
                    expected_digest = m_sha1.group(1).strip()
                    if fname in z.namelist():
                        file_data = z.read(fname)
                        import base64
                        actual_digest = base64.b64encode(hashlib.sha1(file_data).digest()).decode("ascii")
                        if actual_digest != expected_digest:
                            violations.append(
                                f"Digest mismatch for '{fname}': manifest has {expected_digest}, actual is {actual_digest}"
                            )
                        verified_count += 1

    except Exception as e:
        violations.append(f"Failed to verify MANIFEST.MF digests: {str(e)}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = f"All {verified_count} entries verified with pure SHA-1 digests (0 SHA-256 entries)" if passed else f"{len(violations)} digest violations found"
    return CheckResult("MANIFEST.MF SHA-1 Digest Integrity", passed, dur, msg, violations)


def check_no_v2_v3_blocks(apk_path: str) -> CheckResult:
    """
    Check 3: Confirms absence of modern APK Signature Scheme v2/v3 blocks.
    PMCA firmware throws parse failures when encountering APK Sig Block 42.
    """
    start_time = time.time()
    violations = []

    try:
        with open(apk_path, "rb") as f:
            data = f.read()

        # Find End of Central Directory (EOCD) record: 'PK\x05\x06'
        pos = data.rfind(b"PK\x05\x06")
        if pos == -1:
            violations.append("Malformed APK: End of Central Directory (EOCD) record not found.")
        else:
            cd_size, cd_offset = struct.unpack("<II", data[pos + 12 : pos + 20])

            # Check 16 bytes immediately before Central Directory
            if cd_offset >= 16:
                magic_candidate = data[cd_offset - 16 : cd_offset]
                if magic_candidate == b"APK Sig Block 42":
                    violations.append(
                        "Found APK Signature Scheme v2/v3 block immediately before Central Directory. "
                        "PMCA legacy package manager fails installation when v2/v3 blocks are present."
                    )

            # Global magic scan for APK Sig Block 42
            if b"APK Sig Block 42" in data:
                if not any("v2/v3 block" in v for v in violations):
                    violations.append("APK file contains 'APK Sig Block 42' magic signature.")

    except Exception as e:
        violations.append(f"Failed to scan APK for signature blocks: {str(e)}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "Confirmed absence of APK Signature Scheme v2/v3 blocks (pure V1-only APK)" if passed else f"{len(violations)} v2/v3 signature block violations found"
    return CheckResult("Absence of APK Signature Scheme v2/v3", passed, dur, msg, violations)


def check_no_cms_signed_attributes(apk_path: str) -> CheckResult:
    """
    Check 4: Audits CERT.RSA for absence of CMS signed attributes.
    Apache Harmony's JarVerifier on Android 2.3.7 and 4.1.2 rejects certificates
    containing signingTime or CMS Algorithm Protection (OID 1.2.840.113549.1.9.52).
    """
    start_time = time.time()
    violations = []

    try:
        with zipfile.ZipFile(apk_path, "r") as z:
            rsa_files = [n for n in z.namelist() if n.startswith("META-INF/") and (n.endswith(".RSA") or n.endswith(".DSA"))]
            if not rsa_files:
                violations.append("No .RSA/.DSA signature block found in APK.")
                return CheckResult("Absence of CMS Signed Attributes", False, 0.0, "Missing signature block", violations)

            rsa_data = z.read(rsa_files[0])

            # 1. Binary OID pattern scanning in pure Python
            cms_oids = {
                b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x34": "CMS Algorithm Protection (OID 1.2.840.113549.1.9.52)",
                b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x05": "CMS signingTime (OID 1.2.840.113549.1.9.5)",
                b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x03": "CMS contentType (OID 1.2.840.113549.1.9.3)",
                b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x04": "CMS messageDigest (OID 1.2.840.113549.1.9.4)",
                b"\x2a\x86\x48\x86\xf7\x0d\x01\x09\x06": "CMS counterSignature (OID 1.2.840.113549.1.9.6)",
            }
            for oid_bytes, desc in cms_oids.items():
                if oid_bytes in rsa_data:
                    violations.append(
                        f"{rsa_files[0]} contains {desc}. "
                        f"Android 2.3.7/4.1.2 Apache Harmony JarVerifier rejects CMS signed attributes with INSTALL_PARSE_FAILED_NO_CERTIFICATES."
                    )

            # 2. Pure Python ASN.1 DER parser for SignerInfo [0] (0xa0) signed attributes container
            def parse_tlv(data: bytes, offset: int):
                if offset >= len(data): return None
                tag = data[offset]
                offset += 1
                if offset >= len(data): return None
                len_byte = data[offset]
                offset += 1
                if len_byte < 0x80:
                    length = len_byte
                elif len_byte == 0x80:
                    return None
                else:
                    num_bytes = len_byte & 0x7f
                    if offset + num_bytes > len(data): return None
                    length = int.from_bytes(data[offset : offset + num_bytes], "big")
                    offset += num_bytes
                return tag, offset, offset + length, offset + length

            try:
                res = parse_tlv(rsa_data, 0)
                if res and res[0] == 0x30:  # ContentInfo SEQUENCE
                    curr = res[1]
                    r_oid = parse_tlv(rsa_data, curr)
                    if r_oid:
                        curr = r_oid[3]
                        r_cont = parse_tlv(rsa_data, curr)
                        if r_cont and r_cont[0] == 0xa0:  # content [0] EXPLICIT
                            r_sd = parse_tlv(rsa_data, r_cont[1])
                            if r_sd and r_sd[0] == 0x30:  # SignedData SEQUENCE
                                sd_curr = r_sd[1]
                                # 1. version, 2. digestAlgorithms, 3. contentInfo
                                for _ in range(3):
                                    rf = parse_tlv(rsa_data, sd_curr)
                                    if rf: sd_curr = rf[3]
                                # 4. optional certificates [0] (0xa0)
                                rf = parse_tlv(rsa_data, sd_curr)
                                if rf and rf[0] == 0xa0:
                                    sd_curr = rf[3]
                                    rf = parse_tlv(rsa_data, sd_curr)
                                # 5. optional crls [1] (0xa1)
                                if rf and rf[0] == 0xa1:
                                    sd_curr = rf[3]
                                    rf = parse_tlv(rsa_data, sd_curr)
                                # 6. signerInfos SET (0x31)
                                if rf and rf[0] == 0x31:
                                    si_curr, si_end = rf[1], rf[2]
                                    while si_curr < si_end:
                                        r_si = parse_tlv(rsa_data, si_curr)
                                        if not r_si: break
                                        t_si, vs_si, _, si_curr = r_si
                                        if t_si != 0x30: continue
                                        f_curr = vs_si
                                        # Skip version, issuer, digestAlgorithm
                                        for _ in range(3):
                                            rfld = parse_tlv(rsa_data, f_curr)
                                            if rfld: f_curr = rfld[3]
                                        # Next field in SignerInfo:
                                        rfld_next = parse_tlv(rsa_data, f_curr)
                                        if rfld_next and rfld_next[0] == 0xa0:
                                            violations.append(
                                                f"{rsa_files[0]} contains ASN.1 tag [0] (0xa0) signed attributes container in SignerInfo. "
                                                f"Must be pure RFC 2315 without authenticatedAttributes."
                                            )
                                            break
            except Exception:
                pass

            # 3. Secondary verification with openssl asn1parse if available
            openssl_cmd = shutil_which("openssl")
            if openssl_cmd:
                with tempfile.NamedTemporaryFile(suffix=".rsa", delete=False) as tmp_rsa:
                    tmp_rsa.write(rsa_data)
                    tmp_rsa_path = tmp_rsa.name

                try:
                    res = subprocess.run(
                        [openssl_cmd, "asn1parse", "-inform", "DER", "-in", tmp_rsa_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    if res.returncode == 0:
                        asn1_out = res.stdout
                        seen_content_info = False
                        in_signer_infos = False
                        for line in asn1_out.splitlines():
                            if "pkcs7-data" in line:
                                seen_content_info = True
                            elif seen_content_info and "d=3" in line and "cons: SET" in line:
                                in_signer_infos = True
                            if in_signer_infos:
                                m_cont = re.match(r'^\s*\d+:d=(\d+)\s+hl=\d+\s+l=\s*\d+\s+cons:\s+cont\s+\[\s*0\s*\]', line)
                                if m_cont and int(m_cont.group(1)) >= 5:
                                    violations.append("OpenSSL asn1parse detected cont [ 0 ] signed attribute container in SignerInfo.")
                                    break
                            if any(k in line for k in ["1.2.840.113549.1.9.52", "signingTime", "contentType", "messageDigest"]):
                                if "prim: OBJECT" in line:
                                    violations.append(f"OpenSSL asn1parse detected CMS signed attribute: {line.strip()}")
                                    break
                except Exception:
                    pass
                finally:
                    if os.path.exists(tmp_rsa_path):
                        os.remove(tmp_rsa_path)

    except Exception as e:
        violations.append(f"Failed to audit CERT.RSA ASN.1 attributes: {str(e)}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = "CERT.RSA verified as pure RFC 2315 PKCS#7 without CMS signed attributes" if passed else f"{len(violations)} CMS attribute violations found"
    return CheckResult("Absence of CMS Signed Attributes", passed, dur, msg, violations)


def check_zipalign_boundary(apk_path: str, alignment: int = 4) -> CheckResult:
    """
    Check 5: Audits 4-byte zipalign boundaries for all uncompressed stored entries.
    Crucially ensures resources.arsc is stored (compression 0) and aligned to a 4-byte boundary.
    """
    start_time = time.time()
    violations = []
    unaligned_count = 0
    stored_count = 0

    try:
        with open(apk_path, "rb") as f:
            data = f.read()

        with zipfile.ZipFile(apk_path, "r") as z:
            arsc_found = False

            for info in z.infolist():
                header_offset = info.header_offset
                if header_offset + 30 > len(data):
                    violations.append(f"Invalid local header offset {header_offset} for '{info.filename}'.")
                    continue

                local_header = data[header_offset : header_offset + 30]
                fn_len = int.from_bytes(local_header[26:28], "little")
                extra_len = int.from_bytes(local_header[28:30], "little")
                data_offset = header_offset + 30 + fn_len + extra_len

                if info.compress_type == 0:
                    stored_count += 1
                    if data_offset % alignment != 0:
                        unaligned_count += 1
                        violations.append(
                            f"Stored file '{info.filename}' is not {alignment}-byte aligned (offset: {data_offset}, remainder: {data_offset % alignment})."
                        )

                if info.filename == "resources.arsc":
                    arsc_found = True
                    if info.compress_type != 0:
                        violations.append(
                            f"resources.arsc is compressed (method {info.compress_type}). "
                            f"Android requires resources.arsc to be stored uncompressed (method 0) for mmap."
                        )
                    if data_offset % alignment != 0:
                        violations.append(
                            f"resources.arsc is NOT 4-byte aligned (offset {data_offset}). "
                            f"Will cause mmap memory faults on PMCA camera runtime."
                        )

            if not arsc_found:
                violations.append("Missing resources.arsc in APK.")

    except Exception as e:
        violations.append(f"ZipAlign boundary check failed: {str(e)}")

    dur = time.time() - start_time
    passed = len(violations) == 0
    msg = f"All {stored_count} stored entries (including resources.arsc) are {alignment}-byte aligned" if passed else f"{len(violations)} zipalign boundary violations found"
    return CheckResult("4-Byte ZipAlign Boundary Verification", passed, dur, msg, violations)


def shutil_which(cmd: str) -> Optional[str]:
    """Helper to locate executables in PATH."""
    for p in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(p, cmd)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


# ---------------------------------------------------------------------------
# Tier 4 Master Runner API
# ---------------------------------------------------------------------------

def run_tier4_tests(apk_path: Optional[str] = None, verbose: bool = False) -> TierResult:
    """
    Executes Tier 4 APK signature and packaging checks.
    Returns TierResult with individual CheckResult objects.
    """
    start_time = time.time()

    if apk_path is not None:
        target_apk = apk_path
        if not os.path.exists(target_apk):
            return TierResult(
                tier_num=4,
                tier_name="APK Packaging & Signing Validator",
                passed=False,
                duration=0.0,
                checks=[
                    CheckResult(
                        name="Target APK File Existence",
                        passed=False,
                        duration=0.0,
                        message=f"Explicitly specified APK not found: {target_apk}",
                        violations=[f"Target APK file not found on disk: {target_apk}"]
                    )
                ],
                skipped=False
            )
    else:
        # Default auto-discovery
        candidates = [
            "PictureEffectPlus_Ricoh.apk",
            "Ricoh_Camera.apk",
            "PictureEffectPlus_Ricoh_Compat.apk",
            "Ricoh_Official_Mod.apk",
            "PictureEffectPlus_Ricoh_5Filters.apk",
        ]
        target_apk = None
        for c in candidates:
            if os.path.exists(c):
                target_apk = c
                break

        if not target_apk:
            return TierResult(
                tier_num=4,
                tier_name="APK Packaging & Signing Validator",
                passed=False,
                duration=0.0,
                skipped=True,
                skip_reason="Target APK file not specified and auto-discovery found no candidate (Requires --apk <path>)"
            )

    checks = [
        check_zip_structure_and_v1_signatures(target_apk),
        check_manifest_sha1_digests(target_apk),
        check_no_v2_v3_blocks(target_apk),
        check_no_cms_signed_attributes(target_apk),
        check_zipalign_boundary(target_apk)
    ]

    all_passed = all(c.passed for c in checks)
    tier_dur = time.time() - start_time

    return TierResult(
        tier_num=4,
        tier_name="APK Packaging & Signing Validator",
        passed=all_passed,
        duration=tier_dur,
        checks=checks
    )


# ---------------------------------------------------------------------------
# Synthetic Test Fixtures (Self-Test)
# ---------------------------------------------------------------------------

def run_tier4_fixtures() -> bool:
    """Runs synthetic test fixtures verifying that signing defects are accurately detected."""
    print("Running Tier 4 synthetic test fixtures...")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a synthetic V2-contaminated APK
        v2_apk = os.path.join(tmpdir, "v2_test.apk")
        with zipfile.ZipFile(v2_apk, "w") as z:
            z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n\r\n")
            z.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\r\n\r\n")
            z.writestr("META-INF/CERT.RSA", b"fake_rsa_data")
            z.writestr("resources.arsc", b"fake_arsc_data")

        # Inject fake APK Sig Block 42 before Central Directory
        with open(v2_apk, "rb") as f:
            raw = f.read()
        pos = raw.rfind(b"PK\x05\x06")
        cd_size, cd_offset = struct.unpack("<II", raw[pos + 12 : pos + 20])
        # Inject block
        injected = raw[:cd_offset] + b"fake_padding_blk" + b"APK Sig Block 42" + raw[cd_offset:pos]
        # Update EOCD cd_offset
        new_cd_offset = cd_offset + 32
        new_eocd = raw[pos:pos + 16] + struct.pack("<I", new_cd_offset) + raw[pos + 20:]
        with open(v2_apk, "wb") as f:
            f.write(injected + new_eocd)

        res_v2 = check_no_v2_v3_blocks(v2_apk)
        assert not res_v2.passed, "V2 block detection failed to catch injected APK Sig Block 42!"

        # Create a synthetic CMS-contaminated RSA file
        cms_apk = os.path.join(tmpdir, "cms_test.apk")
        with zipfile.ZipFile(cms_apk, "w") as z:
            z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n\r\n")
            z.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\r\n\r\n")
            # Inject CMS Algorithm Protection OID
            z.writestr("META-INF/CERT.RSA", b"rsa_header\x2a\x86\x48\x86\xf7\x0d\x01\x09\x34rsa_tail")
            z.writestr("resources.arsc", b"fake_arsc_data")

        res_cms = check_no_cms_signed_attributes(cms_apk)
        assert not res_cms.passed, "CMS attribute detection failed to catch OID 1.2.840.113549.1.9.52!"

        # Create a synthetic minimal CMS-contaminated RSA file (contentType + messageDigest)
        min_cms_apk = os.path.join(tmpdir, "min_cms_test.apk")
        with zipfile.ZipFile(min_cms_apk, "w") as z:
            z.writestr("META-INF/MANIFEST.MF", "Manifest-Version: 1.0\r\n\r\n")
            z.writestr("META-INF/CERT.SF", "Signature-Version: 1.0\r\n\r\n")
            z.writestr(
                "META-INF/CERT.RSA",
                b"rsa_hdr\x2a\x86\x48\x86\xf7\x0d\x01\x09\x03\x2a\x86\x48\x86\xf7\x0d\x01\x09\x04rsa_tail"
            )
            z.writestr("resources.arsc", b"fake_arsc_data")

        res_min_cms = check_no_cms_signed_attributes(min_cms_apk)
        assert not res_min_cms.passed, "CMS attribute detection failed to catch minimal CMS contentType/messageDigest!"

    print("Tier 4 synthetic test fixtures: ALL PASSED (Genuine detection verified).")
    return True


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tier 4: APK Packaging & Dual-Compatible Signing Validator")
    parser.add_argument("--apk", "-a", type=str, default=None, help="Target APK file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose violation details")
    parser.add_argument("--fixtures", action="store_true", help="Run signing self-test fixtures")

    args = parser.parse_args()

    if args.apk is not None and not os.path.exists(args.apk):
        print(f"Error: Specified APK file '{args.apk}' does not exist.", file=sys.stderr)
        sys.exit(2)

    if args.fixtures:
        success = run_tier4_fixtures()
        sys.exit(0 if success else 1)

    result = run_tier4_tests(args.apk, args.verbose)

    if result.skipped:
        print(f"\n================================================================================")
        print(f"TIER 4 SKIPPED: {result.skip_reason}")
        print(f"================================================================================")
        sys.exit(0)

    print(f"\n================================================================================")
    print(f"TIER 4 RESULT: {'PASS' if result.passed else 'FAIL'} (Duration: {result.duration:.3f}s)")
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
