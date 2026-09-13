#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D LUT (.cube) Decomposer for Sony PMCA BIONZ X ISP:
Decomposes arbitrary 3D LUTs into:
1. 1024-point 10-bit ExtendedGammaTable tone curve g(x)
2. 3x3 Q10 RGB fixed-point color matrix M (sum(row) == 1024)
Evaluates reconstruction fidelity and ground truth accuracy against Ricoh GR III.
"""

import os
import sys
import json
import argparse
import numpy as np

WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from tools.color_bench.core.color_metrics import srgb_to_lab, delta_e_ciede2000

def format_smali_matrix(matrix_3x3):
    flat = np.asarray(matrix_3x3).flatten()
    lines = []
    for val in flat:
        if val >= 0:
            lines.append(f"        0x{val:x}")
        else:
            lines.append(f"        -0x{-val:x}")
    return "\n".join(lines)

def load_cube(filepath):
    """Parses a standard .cube 3D LUT file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cube file not found: {filepath}")
        
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        
    size = None
    title = ""
    data = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("TITLE"):
            title = line[5:].strip().strip('"').strip("'")
            continue
        if line.startswith("LUT_3D_SIZE"):
            size = int(line.split()[1])
            continue
        if line.startswith("DOMAIN_"):
            continue
            
        parts = line.split()
        if len(parts) == 3:
            data.append([float(parts[0]), float(parts[1]), float(parts[2])])
            
    if size is None or len(data) != size ** 3:
        raise ValueError(f"Invalid .cube format: expected {size**3 if size else '?'} points, got {len(data)}")
        
    cube_data = np.array(data, dtype=np.float64).reshape((size, size, size, 3))
    return size, cube_data, title

def sample_cube(cube, size, rgb_float):
    """Trilinear interpolation of 3D color cube."""
    rgb = np.asarray(rgb_float, dtype=np.float64)
    r = np.clip(rgb[:, 0] * (size - 1), 0, size - 1)
    g = np.clip(rgb[:, 1] * (size - 1), 0, size - 1)
    b = np.clip(rgb[:, 2] * (size - 1), 0, size - 1)
    
    r0 = np.floor(r).astype(int); r1 = np.minimum(r0 + 1, size - 1); dr = (r - r0)[:, None]
    g0 = np.floor(g).astype(int); g1 = np.minimum(g0 + 1, size - 1); dg = (g - g0)[:, None]
    b0 = np.floor(b).astype(int); b1 = np.minimum(b0 + 1, size - 1); db = (b - b0)[:, None]
    
    c000 = cube[b0, g0, r0]; c100 = cube[b0, g0, r1]
    c010 = cube[b0, g1, r0]; c110 = cube[b0, g1, r1]
    c001 = cube[b1, g0, r0]; c101 = cube[b1, g0, r1]
    c011 = cube[b1, g1, r0]; c111 = cube[b1, g1, r1]
    
    c00 = c000 * (1.0 - dr) + c100 * dr
    c01 = c001 * (1.0 - dr) + c101 * dr
    c10 = c010 * (1.0 - dr) + c110 * dr
    c11 = c011 * (1.0 - dr) + c111 * dr
    
    c0 = c00 * (1.0 - dg) + c10 * dg
    c1 = c01 * (1.0 - dg) + c11 * dg
    
    return np.clip(c0 * (1.0 - db) + c1 * db, 0.0, 1.0)

def decompose_cube(cube_path, grid_resolution=17):
    """
    Decomposes 3D LUT into 1024-point gamma table and 3x3 row-sum normalized matrix.
    """
    size, cube, title = load_cube(cube_path)
    
    # 1. Neutral diagonal transfer function g(x) across 1024 knots
    x_knots = np.linspace(0.0, 1.0, 1024)
    neutral_pts = np.column_stack([x_knots, x_knots, x_knots])
    neutral_out = sample_cube(cube, size, neutral_pts)
    
    # Photometric luminance transfer (Rec.709 OETF coefficients)
    lum = 0.2126 * neutral_out[:, 0] + 0.7152 * neutral_out[:, 1] + 0.0722 * neutral_out[:, 2]
    gamma_1024 = np.round(np.clip(lum * 1023.0, 0, 1023)).astype(int)
    
    # 2. Dense grid sampling across color space
    ticks = np.linspace(0.0, 1.0, grid_resolution)
    rr, gg, bb = np.meshgrid(ticks, ticks, ticks, indexing="ij")
    grid_in = np.column_stack([rr.ravel(), gg.ravel(), bb.ravel()])
    grid_target = sample_cube(cube, size, grid_in)
    
    # Apply gamma to grid inputs
    idx = np.clip(grid_in * 1023.0, 0, 1023)
    idx_floor = np.floor(idx).astype(int)
    idx_ceil = np.minimum(idx_floor + 1, 1023)
    frac = idx - idx_floor
    grid_gx = (gamma_1024[idx_floor] + frac * (gamma_1024[idx_ceil] - gamma_1024[idx_floor])) / 1023.0
    
    # 3. Constrained linear least squares for matrix M
    # Each row satisfies: sum_j M_ij = 1.0
    mat_3x3 = np.zeros((3, 3), dtype=np.float64)
    A = np.column_stack([grid_gx[:, 0] - grid_gx[:, 2], grid_gx[:, 1] - grid_gx[:, 2]])
    for i in range(3):
        b = grid_target[:, i] - grid_gx[:, 2]
        sol, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        m0, m1 = sol[0], sol[1]
        m2 = 1.0 - m0 - m1
        mat_3x3[i] = [m0, m1, m2]
        
    mat_q10 = np.round(mat_3x3 * 1024.0).astype(int)
    for i in range(3):
        mat_q10[i, i] += 1024 - np.sum(mat_q10[i])
        
    return {
        "title": title,
        "cube_size": size,
        "gamma_1024": gamma_1024.tolist(),
        "matrix_q10": mat_q10.tolist(),
        "cube_raw": (cube, size)
    }

def format_gamma_smali_bytes(gamma_1024):
    """Formats 1024 16-bit integers into PMCA Smali array-data byte stream."""
    b = bytearray()
    for v in gamma_1024:
        b.append(v & 0xff)
        b.append((v >> 8) & 0xff)
    lines = []
    for i in range(0, len(b), 16):
        chunk = b[i:i+16]
        hex_str = " ".join(f"0x{byte:02x}t" for byte in chunk)
        lines.append(f"        {hex_str}")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Decompose 3D .cube LUT into Sony PMCA Gamma Table and Matrix")
    parser.add_argument("--cube", required=True, help="Path to .cube file")
    parser.add_argument("--preset", default=None, choices=["pop-color", "retro-photo", "richtone-mono"],
                        help="Optional preset key to benchmark against DPReview Ricoh GR III ground truth")
    args = parser.parse_args()
    
    print(f"\n=========================================================================")
    print(f"       3D LUT Decomposer for Sony PMCA Hardware ISP                      ")
    print(f"=========================================================================\n")
    print(f"Source LUT: {args.cube}")
    
    decomp = decompose_cube(args.cube)
    gamma = np.array(decomp["gamma_1024"])
    mat_q10 = np.array(decomp["matrix_q10"])
    cube, size = decomp["cube_raw"]
    
    print(f"Title: {decomp['title'] or '(No title)'}")
    print(f"LUT 3D Size: {decomp['cube_size']}^3 ({decomp['cube_size']**3:,} color points)")
    print(f"\n[Extracted 1024-Point 10-bit Gamma Table]:")
    print(f"  Black Pedestal (index 0):   {gamma[0]} (sRGB {gamma[0]/1023.0*255.0:.1f})")
    print(f"  Midtone Center (index 512): {gamma[512]} (sRGB {gamma[512]/1023.0*255.0:.1f})")
    print(f"  Highlight Peak (index 1023):{gamma[1023]} (sRGB {gamma[1023]/1023.0*255.0:.1f})")
    
    print(f"\n[Extracted 3x3 Fixed-Point RGB Matrix (Q10)] (Row Sum = 1024):")
    for r in mat_q10:
        print(f"  [{r[0]:5d}, {r[1]:5d}, {r[2]:5d}]  -> Sum: {np.sum(r)}")
        
    # Self-reconstruction test on standard 24 ColorChecker patches
    ref_path = os.path.join(os.path.dirname(__file__), "data", "dpreview_gr3_reference.json")
    with open(ref_path) as f:
        ref_data = json.load(f)
        
    patches = np.array([p["standard_srgb"] for p in ref_data["patches"]], dtype=np.float64) / 255.0
    target_3d = sample_cube(cube, size, patches) * 255.0
    
    idx = np.clip(patches * 1023.0, 0, 1023)
    idx_floor = np.floor(idx).astype(int); idx_ceil = np.minimum(idx_floor + 1, 1023); frac = idx - idx_floor
    gx = (gamma[idx_floor] + frac * (gamma[idx_ceil] - gamma[idx_floor])) / 1023.0 * 255.0
    out_decomposed = np.clip(np.dot(gx, (mat_q10 / 1024.0).T), 0, 255)
    
    de_recon = delta_e_ciede2000(srgb_to_lab(out_decomposed), srgb_to_lab(target_3d))
    print(f"\n[Reconstruction Fidelity] (Decomposed 1D+Matrix vs Full 3D LUT):")
    print(f"  Average ΔE00: {np.mean(de_recon):.2f} (Perceptual loss due to 1D+3x3 decomposition)")
    print(f"  Max ΔE00:     {np.max(de_recon):.2f}")
    
    if args.preset:
        gt_srgb = np.array(ref_data["presets"][args.preset]["ground_truth_srgb"], dtype=np.float64)
        de_gt_3d = delta_e_ciede2000(srgb_to_lab(target_3d), srgb_to_lab(gt_srgb))
        de_gt_decomp = delta_e_ciede2000(srgb_to_lab(out_decomposed), srgb_to_lab(gt_srgb))
        
        print(f"\n[Accuracy vs Authentic Ricoh GR III Ground Truth] ({args.preset}):")
        print(f"  Full 3D LUT vs Ricoh GR III:         Avg ΔE00 = {np.mean(de_gt_3d):.2f}")
        print(f"  Decomposed Hardware vs Ricoh GR III: Avg ΔE00 = {np.mean(de_gt_decomp):.2f}")
        
    print(f"\n[Smali Matrix Representation]:")
    print(format_smali_matrix(mat_q10))

if __name__ == "__main__":
    main()
