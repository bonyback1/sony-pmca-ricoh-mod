# -*- coding: utf-8 -*-
"""
Color metrics and color space conversions for Sony PMCA vs Ricoh GR benchmark.
Implements sRGB <-> linear, sRGB <-> XYZ <-> Lab, and CIEDE2000 (Sharma et al. 2005).
"""

import math
import numpy as np

# Standard D65 white point (2-degree observer)
XN = 95.0489
YN = 100.0000
ZN = 108.8840

def srgb_to_linear(rgb):
    """Converts sRGB [0..255] or [0..1] to linear RGB [0..1]."""
    rgb = np.asarray(rgb, dtype=np.float64)
    if np.max(rgb) > 1.0:
        rgb = rgb / 255.0
    
    linear = np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        np.power((rgb + 0.055) / 1.055, 2.4)
    )
    return linear

def linear_to_srgb(linear):
    """Converts linear RGB [0..1] to sRGB [0..255]."""
    linear = np.asarray(linear, dtype=np.float64)
    linear = np.clip(linear, 0.0, 1.0)
    
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * np.power(linear, 1.0 / 2.4) - 0.055
    )
    return np.clip(srgb * 255.0, 0.0, 255.0)

# sRGB D65 to XYZ matrix
M_SRGB_TO_XYZ = np.array([
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041]
], dtype=np.float64)

M_XYZ_TO_SRGB = np.linalg.inv(M_SRGB_TO_XYZ)

def srgb_to_xyz(rgb):
    """Converts sRGB [0..255] to CIE XYZ [0..100]."""
    lin = srgb_to_linear(rgb)
    if lin.ndim == 1:
        xyz = np.dot(M_SRGB_TO_XYZ, lin) * 100.0
    else:
        xyz = np.dot(lin, M_SRGB_TO_XYZ.T) * 100.0
    return xyz

def xyz_to_srgb(xyz):
    """Converts CIE XYZ [0..100] to sRGB [0..255]."""
    xyz_norm = np.asarray(xyz, dtype=np.float64) / 100.0
    if xyz_norm.ndim == 1:
        lin = np.dot(M_XYZ_TO_SRGB, xyz_norm)
    else:
        lin = np.dot(xyz_norm, M_XYZ_TO_SRGB.T)
    return linear_to_srgb(lin)

def xyz_to_lab(xyz):
    """Converts CIE XYZ [0..100] to CIE L*a*b*."""
    xyz = np.asarray(xyz, dtype=np.float64)
    if xyz.ndim == 1:
        x, y, z = xyz[0] / XN, xyz[1] / YN, xyz[2] / ZN
    else:
        x, y, z = xyz[..., 0] / XN, xyz[..., 1] / YN, xyz[..., 2] / ZN
        
    delta = 6.0 / 29.0
    
    def f(t):
        return np.where(t > delta**3, np.cbrt(t), t / (3.0 * delta**2) + 4.0 / 29.0)
        
    fx, fy, fz = f(x), f(y), f(z)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    
    if xyz.ndim == 1:
        return np.array([L, a, b])
    return np.stack([L, a, b], axis=-1)

def lab_to_xyz(lab):
    """Converts CIE L*a*b* to CIE XYZ [0..100]."""
    lab = np.asarray(lab, dtype=np.float64)
    if lab.ndim == 1:
        L, a, b = lab[0], lab[1], lab[2]
    else:
        L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
        
    fy = (L + 16.0) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b / 200.0
    
    delta = 6.0 / 29.0
    
    def f_inv(t):
        return np.where(t > delta, t**3, 3.0 * delta**2 * (t - 4.0 / 29.0))
        
    x = f_inv(fx) * XN
    y = f_inv(fy) * YN
    z = f_inv(fz) * ZN
    
    if lab.ndim == 1:
        return np.array([x, y, z])
    return np.stack([x, y, z], axis=-1)

def srgb_to_lab(rgb):
    """Direct conversion from sRGB [0..255] to CIE L*a*b*."""
    return xyz_to_lab(srgb_to_xyz(rgb))

def lab_to_srgb(lab):
    """Direct conversion from CIE L*a*b* to sRGB [0..255]."""
    return xyz_to_srgb(lab_to_xyz(lab))

def delta_e_76(lab1, lab2):
    """Classic CIE 1976 Euclidean color difference."""
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    return np.sqrt(np.sum((lab1 - lab2)**2, axis=-1))

def delta_e_ciede2000(lab1, lab2, kL=1.0, kC=1.0, kH=1.0):
    """
    Computes CIEDE2000 color difference between two Lab colors.
    Reference: Gaurav Sharma et al. (2005) 'The CIEDE2000 color-difference formula'.
    Supports single color pair or array of color pairs.
    """
    lab1 = np.asarray(lab1, dtype=np.float64)
    lab2 = np.asarray(lab2, dtype=np.float64)
    
    # Ensure shape consistency
    single = False
    if lab1.ndim == 1 and lab2.ndim == 1:
        lab1 = lab1[np.newaxis, :]
        lab2 = lab2[np.newaxis, :]
        single = True

    L1, a1, b1 = lab1[:, 0], lab1[:, 1], lab1[:, 2]
    L2, a2, b2 = lab2[:, 0], lab2[:, 1], lab2[:, 2]

    # Step 1: Calculate C1, C2, C_bar, and G factor
    C1 = np.hypot(a1, b1)
    C2 = np.hypot(a2, b2)
    C_bar = 0.5 * (C1 + C2)
    C_bar7 = C_bar**7
    G = 0.5 * (1.0 - np.sqrt(C_bar7 / (C_bar7 + 25.0**7 + 1e-12)))

    # a-prime
    a1_prime = (1.0 + G) * a1
    a2_prime = (1.0 + G) * a2

    # C-prime
    C1_prime = np.hypot(a1_prime, b1)
    C2_prime = np.hypot(a2_prime, b2)

    # h-prime in degrees [0, 360)
    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360.0
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360.0

    # Step 2: Calculate dL_prime, dC_prime, dh_prime, dH_prime
    dL_prime = L2 - L1
    dC_prime = C2_prime - C1_prime

    # dh_prime
    h_diff = h2_prime - h1_prime
    dh_prime = np.zeros_like(h_diff)
    
    mask_c = (C1_prime * C2_prime) != 0
    mask1 = mask_c & (np.abs(h_diff) <= 180.0)
    mask2 = mask_c & (h_diff > 180.0)
    mask3 = mask_c & (h_diff < -180.0)
    
    dh_prime[mask1] = h_diff[mask1]
    dh_prime[mask2] = h_diff[mask2] - 360.0
    dh_prime[mask3] = h_diff[mask3] + 360.0

    dH_prime = 2.0 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(0.5 * dh_prime))

    # Step 3: Calculate L_bar_prime, C_bar_prime, h_bar_prime
    L_bar_prime = 0.5 * (L1 + L2)
    C_bar_prime = 0.5 * (C1_prime + C2_prime)

    h_bar_prime = np.zeros_like(h1_prime)
    h_sum = h1_prime + h2_prime
    
    mask_h1 = mask_c & (np.abs(h1_prime - h2_prime) <= 180.0)
    mask_h2 = mask_c & (np.abs(h1_prime - h2_prime) > 180.0) & (h_sum < 360.0)
    mask_h3 = mask_c & (np.abs(h1_prime - h2_prime) > 180.0) & (h_sum >= 360.0)
    
    h_bar_prime[mask_h1] = 0.5 * h_sum[mask_h1]
    h_bar_prime[mask_h2] = 0.5 * (h_sum[mask_h2] + 360.0)
    h_bar_prime[mask_h3] = 0.5 * (h_sum[mask_h3] - 360.0)
    h_bar_prime[~mask_c] = h_sum[~mask_c]

    # T factor
    T = (1.0 - 0.17 * np.cos(np.radians(h_bar_prime - 30.0))
             + 0.24 * np.cos(np.radians(2.0 * h_bar_prime))
             + 0.32 * np.cos(np.radians(3.0 * h_bar_prime + 6.0))
             - 0.20 * np.cos(np.radians(4.0 * h_bar_prime - 63.0)))

    # Weighting factors SL, SC, SH
    L_bar_sq = (L_bar_prime - 50.0)**2
    SL = 1.0 + (0.015 * L_bar_sq) / np.sqrt(20.0 + L_bar_sq)
    SC = 1.0 + 0.045 * C_bar_prime
    SH = 1.0 + 0.015 * C_bar_prime * T

    # Rotation term RT
    d_theta = 30.0 * np.exp(-((h_bar_prime - 275.0) / 25.0)**2)
    C_bar_p7 = C_bar_prime**7
    RC = 2.0 * np.sqrt(C_bar_p7 / (C_bar_p7 + 25.0**7 + 1e-12))
    RT = -np.sin(np.radians(2.0 * d_theta)) * RC

    # Total CIEDE2000 color difference
    vL = dL_prime / (kL * SL)
    vC = dC_prime / (kC * SC)
    vH = dH_prime / (kH * SH)

    dE = np.sqrt(vL**2 + vC**2 + vH**2 + RT * vC * vH)
    
    if single:
        return float(dE[0])
    return dE

def compute_chroma(a, b):
    """Computes CIE Chroma C*."""
    return np.hypot(a, b)

def compute_hue_angle(a, b):
    """Computes CIE Hue angle in degrees [0, 360)."""
    return np.degrees(np.arctan2(b, a)) % 360.0
