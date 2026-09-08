#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Android APK Signer compatible with Android 4.1.2 (Apache Harmony / Dalvik).
Uses OpenSSL pkcs7/smime -noattr -binary to avoid modern CMS Protect attributes
that cause INSTALL_PARSE_FAILED_NO_CERTIFICATES on legacy Android camera runtimes.
"""

import os
import sys
import shutil
import zipfile
import hashlib
import base64
import subprocess
import tempfile
import argparse

def find_openssl():
    path = shutil.which('openssl')
    if path:
        return path
    for candidate in ['/opt/homebrew/bin/openssl', '/usr/local/bin/openssl', '/usr/bin/openssl']:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return 'openssl'

def ensure_pem(pem_path=None):
    if pem_path and os.path.exists(pem_path):
        return pem_path, False
    
    openssl_bin = find_openssl()
    tmp_pem = tempfile.NamedTemporaryFile('w', suffix='.pem', delete=False)
    tmp_pem_path = tmp_pem.name
    tmp_pem.close()
    
    cmd = [
        openssl_bin, 'req', '-x509', '-newkey', 'rsa:2048',
        '-keyout', tmp_pem_path,
        '-out', tmp_pem_path,
        '-days', '10000',
        '-nodes',
        '-subj', '/CN=SonyPMCADebug/O=Community/C=US'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Failed to generate debug certificate via OpenSSL: {res.stderr}")
    return tmp_pem_path, True

def sign_apk(input_apk_path, output_apk_path, pem_path=None):
    if not os.path.exists(input_apk_path):
        raise FileNotFoundError(f"Input APK not found: {input_apk_path}")
        
    actual_pem, is_temp_pem = ensure_pem(pem_path)
    openssl_bin = find_openssl()
    
    print(f"Signing {input_apk_path} -> {output_apk_path}")
    print(f"Using certificate: {'[Auto-generated Debug PEM]' if is_temp_pem else actual_pem}")
    
    try:
        # 1. Read input APK entries (excluding META-INF)
        entries = {}
        with zipfile.ZipFile(input_apk_path, 'r') as zin:
            for item in zin.infolist():
                if item.filename.startswith('META-INF/'):
                    continue
                entries[item.filename] = (item, zin.read(item.filename))
                
        # 2. Build MANIFEST.MF
        manifest_lines = [
            b"Manifest-Version: 1.0\r\n",
            b"Created-By: 1.0 (Android Signer)\r\n",
            b"\r\n"
        ]
        
        manifest_sections = {}
        
        for name in sorted(entries.keys()):
            _, data = entries[name]
            sha1 = base64.b64encode(hashlib.sha1(data).digest()).decode('ascii')
            section = f"Name: {name}\r\nSHA1-Digest: {sha1}\r\n\r\n".encode('utf-8')
            manifest_sections[name] = section
            manifest_lines.append(section)
            
        manifest_bytes = b"".join(manifest_lines)
        
        # 3. Build CERT.SF
        manifest_sha1 = base64.b64encode(hashlib.sha1(manifest_bytes).digest()).decode('ascii')
        sf_lines = [
            b"Signature-Version: 1.0\r\n",
            b"Created-By: 1.0 (Android Signer)\r\n",
            f"SHA1-Digest-Manifest: {manifest_sha1}\r\n".encode('ascii'),
            b"\r\n"
        ]
        
        for name in sorted(entries.keys()):
            sec_bytes = manifest_sections[name]
            sec_sha1 = base64.b64encode(hashlib.sha1(sec_bytes).digest()).decode('ascii')
            sf_section = f"Name: {name}\r\nSHA1-Digest: {sec_sha1}\r\n\r\n".encode('utf-8')
            sf_lines.append(sf_section)
            
        sf_bytes = b"".join(sf_lines)
        
        # 4. Sign CERT.SF using openssl smime -sign -noattr -binary
        with tempfile.NamedTemporaryFile('wb', delete=False) as sf_tmp:
            sf_tmp.write(sf_bytes)
            sf_tmp_path = sf_tmp.name
            
        rsa_tmp_path = sf_tmp_path + ".rsa"
        try:
            cmd = [
                openssl_bin, "smime", "-sign",
                "-in", sf_tmp_path,
                "-outform", "DER",
                "-inkey", actual_pem,
                "-signer", actual_pem,
                "-noattr",
                "-binary",
                "-out", rsa_tmp_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"OpenSSL signature failed: {res.stderr}")
                
            with open(rsa_tmp_path, 'rb') as f:
                rsa_bytes = f.read()
        finally:
            if os.path.exists(sf_tmp_path):
                os.remove(sf_tmp_path)
            if os.path.exists(rsa_tmp_path):
                os.remove(rsa_tmp_path)
            
        # 5. Write output APK
        os.makedirs(os.path.dirname(os.path.abspath(output_apk_path)), exist_ok=True)
        with zipfile.ZipFile(output_apk_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
            zout.writestr('META-INF/MANIFEST.MF', manifest_bytes)
            zout.writestr('META-INF/CERT.SF', sf_bytes)
            zout.writestr('META-INF/CERT.RSA', rsa_bytes)
            
            for name in sorted(entries.keys()):
                item, data = entries[name]
                zout.writestr(item, data)
                
        print(f"Successfully signed APK -> {output_apk_path}")
        print(f"Files signed: {len(entries)}, RSA signature size: {len(rsa_bytes)} bytes")
    finally:
        if is_temp_pem and os.path.exists(actual_pem):
            try:
                os.remove(actual_pem)
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="Sign APK with Android 4.1.2 Harmony-compatible v1 JAR signature")
    parser.add_argument('-i', '--input', required=True, help="Path to input APK")
    parser.add_argument('-o', '--output', required=True, help="Path to output signed APK")
    parser.add_argument('-k', '--key', default=None, help="Path to PEM certificate/private key (auto-generated if omitted)")
    args = parser.parse_args()

    sign_apk(args.input, args.output, args.key)

if __name__ == '__main__':
    main()
