# -*- coding: utf-8 -*-
"""
Closed-Loop Color Optimizer:
Uses constrained optimization (SLSQP via scipy.optimize) to solve for optimal
3x3 RGB color matrix coefficients (Q10 fixed-point) and WB shift adjustments
that minimize CIEDE2000 color difference against Ricoh GR III ground truth.
"""

import numpy as np
from scipy.optimize import minimize
from tools.color_bench.core.color_metrics import srgb_to_lab, delta_e_ciede2000, srgb_to_linear
from tools.color_bench.core.isp_simulator import apply_wb_shift, apply_matrix, apply_gamma

# Patch importance weights (Macbeth 24 patches)
# Skin tones (1, 2) and Sky (3), Foliage (4) have higher perceptual priority
PATCH_WEIGHTS = np.array([
    2.5, 2.5, 2.0, 1.8, 1.0, 1.2,
    1.2, 1.0, 1.2, 1.0, 1.2, 1.2,
    1.0, 1.5, 1.5, 1.2, 1.0, 1.5,
    1.0, 1.0, 1.0, 1.0, 1.0, 1.0
], dtype=np.float64)

def optimize_matrix_for_preset(input_srgbs, target_srgbs, initial_matrix_q10, gamma_table, wb_shifts):
    """
    Solves for the optimal 3x3 matrix under row-sum constraints (sum(row) == 1024).
    """
    inputs = np.asarray(input_srgbs, dtype=np.float64)
    targets = np.asarray(target_srgbs, dtype=np.float64)
    target_labs = srgb_to_lab(targets)
    
    # Pre-compute stage 1 (gamma) & stage 2 (WB shift) since they are independent of matrix M
    gx = apply_gamma(inputs, gamma_table)
    gx_wb = apply_wb_shift(gx, lb=wb_shifts['lb'], cc=wb_shifts['cc'])
    
    # Detect if initial matrix is monochrome (all rows identical)
    m_init = np.asarray(initial_matrix_q10, dtype=np.float64)
    is_monochrome = np.allclose(m_init[0], m_init[1]) and np.allclose(m_init[1], m_init[2])
    
    if is_monochrome:
        x0 = np.array([m_init[0, 0], m_init[0, 1]], dtype=np.float64)
        def unpack_matrix(x):
            row = np.array([x[0], x[1], 1024.0 - x[0] - x[1]], dtype=np.float64)
            return np.array([row, row, row])
        bounds = [(0.0, 1024.0), (0.0, 1024.0)]
    else:
        x0 = np.array([
            m_init[0, 0], m_init[0, 1],
            m_init[1, 0], m_init[1, 1],
            m_init[2, 0], m_init[2, 1]
        ], dtype=np.float64)
        def unpack_matrix(x):
            m = np.zeros((3, 3), dtype=np.float64)
            m[0, 0], m[0, 1] = x[0], x[1]
            m[0, 2] = 1024.0 - x[0] - x[1]
            m[1, 0], m[1, 1] = x[2], x[3]
            m[1, 2] = 1024.0 - x[2] - x[3]
            m[2, 0], m[2, 1] = x[4], x[5]
            m[2, 2] = 1024.0 - x[4] - x[5]
            return m
        bounds = [
            (800.0, 1350.0), (-250.0, 150.0),   # Row 0: R
            (-250.0, 200.0), (800.0, 1350.0),   # Row 1: G
            (-250.0, 150.0), (-250.0, 150.0)    # Row 2: B
        ]

    def loss_function(x):
        m = unpack_matrix(x)
        sim_srgb = apply_matrix(gx_wb, m)
        sim_lab = srgb_to_lab(sim_srgb)
        
        de_vals = delta_e_ciede2000(sim_lab, target_labs)
        weighted_loss = np.sum(de_vals * PATCH_WEIGHTS) / np.sum(PATCH_WEIGHTS)
        
        # Regularization towards initial matrix
        reg = 0.0001 * np.sum((x - x0)**2)
        return weighted_loss + reg
    
    res = minimize(
        loss_function,
        x0,
        method='L-BFGS-B',
        bounds=bounds,
        options={'maxiter': 200, 'ftol': 1e-6}
    )
    
    opt_matrix = np.round(unpack_matrix(res.x)).astype(int)
    # Ensure exact row sum of 1024 for each row
    for i in range(3):
        diff = 1024 - np.sum(opt_matrix[i])
        opt_matrix[i, i] += diff
        
    return opt_matrix, res.fun

def format_smali_matrix(matrix_3x3):
    """Formats a 3x3 matrix into smali array-data hex string."""
    flat = matrix_3x3.flatten()
    lines = []
    for val in flat:
        if val >= 0:
            lines.append(f"        0x{val:x}")
        else:
            lines.append(f"        -0x{-val:x}")
    return "\n".join(lines)
