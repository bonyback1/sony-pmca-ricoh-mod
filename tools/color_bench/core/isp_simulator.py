# -*- coding: utf-8 -*-
"""
ISP Simulator: Faithfully reproduces the Sony BIONZ X ISP processing steps
configured by RicohHook in PMCA:
1. Pre-ISP Hardware White Balance Shift (LB/CC)
2. 3x3 RGB Color Matrix (Q10 fixed-point)
3. 1024-Point 10-bit ExtendedGammaTable tone mapping
"""

import numpy as np
from tools.color_bench.core.color_metrics import srgb_to_linear, linear_to_srgb
from tools.generate_ricoh_hook import (
    gen_curve_pos, gen_curve_neg, gen_curve_hcbw, gen_curve_daido, gen_curve_xpro
)

# Preset configuration in current codebase
PRESETS_CONFIG = {
    'pop-color': {
        'name': 'Ricoh GR Positive Film (理光 GR 正片)',
        'matrix': np.array([
            [991, 203, -170],
            [-21, 1059, -14],
            [48, 260, 716]
        ], dtype=np.float64),
        'curve_gen': gen_curve_pos,
        'wb': {'lb': 0, 'cc': 0}
    },
    'retro-photo': {
        'name': 'Ricoh Negative Film (理光负片)',
        'matrix': np.array([
            [848, -54, 230],
            [169, 641, 214],
            [66, 278, 680]
        ], dtype=np.float64),
        'curve_gen': gen_curve_neg,
        'wb': {'lb': 2, 'cc': 0}
    },
    'richtone-mono': {
        'name': 'High Contrast B&W (高对比黑白)',
        'matrix': np.array([
            [276, 633, 115],
            [276, 633, 115],
            [276, 633, 115]
        ], dtype=np.float64),
        'curve_gen': gen_curve_hcbw,
        'wb': {'lb': 0, 'cc': 0}
    },
    'rough-mono': {
        'name': 'Moriyama Daido B&W (森山大道风)',
        'matrix': np.array([
            [625, 386, 13],
            [625, 386, 13],
            [625, 386, 13]
        ], dtype=np.float64),
        'curve_gen': gen_curve_daido,
        'wb': {'lb': 0, 'cc': 0}
    },
    'watercolor': {
        'name': 'Cross Process (正负逆冲)',
        'matrix': np.array([
            [1141, -69, -48],
            [8, 1031, -15],
            [-19, 41, 1002]
        ], dtype=np.float64),
        'curve_gen': gen_curve_xpro,
        'wb': {'lb': -3, 'cc': 2}
    }
}

def apply_gamma(rgb_val, gamma_table_1024):
    """
    Maps RGB values in range [0..255] through the 1024-point 10-bit Gamma Table.
    Interpolates linearly between discrete table points.
    Returns RGB in range [0..255].
    """
    arr = np.asarray(rgb_val, dtype=np.float64)
    table = np.asarray(gamma_table_1024, dtype=np.float64)
    
    # Scale input [0..255] to table index [0..1023]
    x_idx = np.clip(arr / 255.0 * 1023.0, 0.0, 1023.0)
    
    # 1D linear interpolation
    idx_floor = np.floor(x_idx).astype(np.int32)
    idx_ceil = np.minimum(idx_floor + 1, 1023)
    frac = x_idx - idx_floor
    
    val_floor = table[idx_floor]
    val_ceil = table[idx_ceil]
    
    y_10bit = val_floor + frac * (val_ceil - val_floor)
    
    # Convert 10-bit [0..1023] to RGB [0..255]
    return np.clip(y_10bit / 1023.0 * 255.0, 0.0, 255.0)

def apply_wb_shift(rgb_val, lb=0, cc=0):
    """
    Simulates Sony hardware white balance shift.
    LB: Light Balance [-14, +14] (amber / blue axis, ~2.5% per step)
    CC: Color Compensation [-14, +14] (green / magenta axis, ~2.0% per step)
    """
    arr = np.asarray(rgb_val, dtype=np.float64)
    r_gain = 1.0 + 0.025 * lb
    b_gain = 1.0 - 0.025 * lb
    g_gain = 1.0 + 0.020 * cc
    
    gains = np.array([r_gain, g_gain, b_gain], dtype=np.float64)
    
    if arr.ndim == 1:
        return np.clip(arr * gains, 0.0, 255.0)
    return np.clip(arr * gains[np.newaxis, :], 0.0, 255.0)

def apply_matrix(rgb_val, matrix_q10):
    """
    Applies 3x3 RGB color matrix with Q10 fixed-point scaling (1024 = 1.0).
    """
    arr = np.asarray(rgb_val, dtype=np.float64)
    m = np.asarray(matrix_q10, dtype=np.float64) / 1024.0
    
    if arr.ndim == 1:
        out = np.dot(m, arr)
    else:
        out = np.dot(arr, m.T)
    return np.clip(out, 0.0, 255.0)

def simulate_pipeline(input_srgb, preset_key, custom_matrix=None, custom_gamma=None, custom_wb=None):
    """
    Runs input sRGB values through full simulated camera ISP pipeline:
    out = clip( M · (g(x) * WB_gains) )
    """
    cfg = PRESETS_CONFIG.get(preset_key)
    if not cfg:
        raise ValueError(f"Unknown preset: {preset_key}")
        
    wb_info = custom_wb if custom_wb is not None else cfg['wb']
    matrix = custom_matrix if custom_matrix is not None else cfg['matrix']
    gamma = custom_gamma if custom_gamma is not None else cfg['curve_gen']()
    
    # Stage 1: ExtendedGammaTable 1024-point tone mapping g(x)
    post_gamma = apply_gamma(input_srgb, gamma)
    
    # Stage 2: Hardware White Balance Shift gains
    post_wb = apply_wb_shift(post_gamma, lb=wb_info['lb'], cc=wb_info['cc'])
    
    # Stage 3: 3x3 RGB Fixed-Point Color Matrix M
    out_srgb = apply_matrix(post_wb, matrix)
    
    return out_srgb
