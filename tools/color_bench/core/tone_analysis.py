# -*- coding: utf-8 -*-
"""
Tone Analysis: Evaluates 10-bit tone transfer curves, black pedestal,
highlight roll-off, midtone contrast, and split-toning color bias across gray ramps.
"""

import numpy as np
from tools.color_bench.core.color_metrics import srgb_to_lab

def analyze_curve_properties(curve_1024):
    """
    Analyzes physical characteristics of a 1024-point 10-bit LUT curve.
    """
    arr = np.asarray(curve_1024, dtype=np.float64)
    black_level = arr[0]
    white_level = arr[1023]
    mid_level = arr[512]
    
    # Calculate gradient (local slope) across normalized [0..1] range
    x_norm = np.linspace(0.0, 1.0, 1024)
    y_norm = arr / 1023.0
    slopes = np.gradient(y_norm, x_norm)
    
    center_slope = slopes[512]
    max_slope = np.max(slopes)
    max_slope_idx = np.argmax(slopes)
    
    return {
        'black_level_10bit': int(black_level),
        'white_level_10bit': int(white_level),
        'mid_level_10bit': int(mid_level),
        'black_pedestal_srgb': round(black_level / 1023.0 * 255.0, 1),
        'white_ceiling_srgb': round(white_level / 1023.0 * 255.0, 1),
        'center_slope': round(float(center_slope), 3),
        'max_contrast_slope': round(float(max_slope), 3),
        'max_slope_input_pct': round(float(max_slope_idx / 1023.0 * 100.0), 1)
    }

def analyze_gray_ramp(neutral_srgbs):
    """
    Analyzes the 6-step neutral ramp (Patches 19-24) for split-toning and tone density.
    Returns L*, a*, b*, and highlight vs shadow color differential.
    """
    srgbs = np.asarray(neutral_srgbs, dtype=np.float64)
    labs = srgb_to_lab(srgbs)
    
    # Patches: 0=White, 1=N8, 2=N6.5, 3=N5, 4=N3.5, 5=Black
    white_lab = labs[0]
    black_lab = labs[-1]
    
    # Split toning metric: warm highlights (b* > 0) vs cool shadows (b* < 0 or lower b*)
    split_b = white_lab[2] - black_lab[2]
    split_a = white_lab[1] - black_lab[1]
    
    steps = []
    for i, lab in enumerate(labs):
        steps.append({
            'patch_index': i + 19,
            'srgb': [round(c, 1) for c in srgbs[i]],
            'L': round(float(lab[0]), 2),
            'a': round(float(lab[1]), 2),
            'b': round(float(lab[2]), 2)
        })
        
    return {
        'steps': steps,
        'highlight_warmth_b': round(float(white_lab[2]), 2),
        'shadow_warmth_b': round(float(black_lab[2]), 2),
        'split_toning_delta_b': round(float(split_b), 2),
        'split_toning_delta_a': round(float(split_a), 2)
    }
