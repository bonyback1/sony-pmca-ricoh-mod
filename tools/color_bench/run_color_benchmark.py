#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sony A6300 vs Ricoh GR III Color Science Benchmark Runner.
Measures colorimetric fidelity (CIEDE2000), tone transfer characteristics,
and split-toning accuracy across 5 Ricoh film presets against DPReview studio ground truth.
Optionally runs constrained auto-tuning optimization to minimize Delta E.
"""

import os
import sys
import json
import argparse
import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from tools.color_bench.core.color_metrics import srgb_to_lab, delta_e_ciede2000
from tools.color_bench.core.isp_simulator import (
    PRESETS_CONFIG, simulate_pipeline, apply_matrix, apply_gamma, apply_wb_shift
)
from tools.color_bench.core.tone_analysis import analyze_curve_properties, analyze_gray_ramp
from tools.color_bench.core.optimizer import optimize_matrix_for_preset, format_smali_matrix
from tools.color_bench.report_generator import generate_comparison_figure, generate_html_report

# ANSI colors for terminal output
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_CYAN = "\033[36m"
C_BLUE = "\033[34m"

def load_reference_data():
    ref_path = os.path.join(os.path.dirname(__file__), "data", "dpreview_gr3_reference.json")
    if not os.path.exists(ref_path):
        raise FileNotFoundError(f"Reference data file not found: {ref_path}")
    with open(ref_path, "r", encoding="utf-8") as f:
        return json.load(f)

def run_preset_benchmark(preset_key, ref_data, do_optimize=False, out_dir=None):
    if preset_key not in PRESETS_CONFIG:
        raise ValueError(f"Unknown preset key: {preset_key}")
        
    cfg = PRESETS_CONFIG[preset_key]
    preset_name = cfg["name"]
    ref_preset = ref_data["presets"].get(preset_key)
    if not ref_preset:
        raise ValueError(f"Preset {preset_key} not found in reference data.")
        
    standard_patches = ref_data["patches"]
    input_srgbs = np.array([p["standard_srgb"] for p in standard_patches], dtype=np.float64)
    ground_truth_srgbs = np.array(ref_preset["ground_truth_srgb"], dtype=np.float64)
    
    # 1. Run simulated BIONZ X ISP pipeline
    simulated_srgbs = simulate_pipeline(input_srgbs, preset_key)
    
    # 2. Compute Lab and CIEDE2000 color differences
    sim_labs = srgb_to_lab(simulated_srgbs)
    gt_labs = srgb_to_lab(ground_truth_srgbs)
    de_vals = delta_e_ciede2000(sim_labs, gt_labs)
    
    avg_de = float(np.mean(de_vals))
    max_de = float(np.max(de_vals))
    max_idx = int(np.argmax(de_vals))
    worst_patch = standard_patches[max_idx]["name"]
    
    # Per-patch results for plotting & reports
    patch_results = []
    for i, p in enumerate(standard_patches):
        patch_results.append({
            "id": p["id"],
            "name": p["name"],
            "simulated_srgb": [int(round(c)) for c in simulated_srgbs[i]],
            "ground_truth_srgb": [int(round(c)) for c in ground_truth_srgbs[i]],
            "simulated_lab": [round(float(v), 2) for v in sim_labs[i]],
            "ground_truth_lab": [round(float(v), 2) for v in gt_labs[i]],
            "delta_e00": round(float(de_vals[i]), 2)
        })
        
    # 3. Tone and neutral ramp analysis
    curve_1024 = cfg["curve_gen"]()
    tone_props = analyze_curve_properties(curve_1024)
    gray_ramp_analysis = analyze_gray_ramp(simulated_srgbs[18:24])
    
    summary = {
        "key": preset_key,
        "name": preset_name,
        "avg_delta_e00": round(avg_de, 2),
        "max_delta_e00": round(max_de, 2),
        "worst_patch": f"#{max_idx+1} {worst_patch} (ΔE {max_de:.2f})",
        "tone": tone_props,
        "gray_ramp": gray_ramp_analysis,
        "patch_results": patch_results,
        "figure_rel_path": None,
        "optimized_matrix": None,
        "optimized_loss": None,
        "optimized_smali": None
    }
    
    # 4. Optional: Closed-Loop Optimization
    if do_optimize:
        opt_mat, opt_loss = optimize_matrix_for_preset(
            input_srgbs, ground_truth_srgbs, cfg["matrix"], curve_1024, cfg["wb"]
        )
        # Evaluate simulated performance with optimized matrix
        opt_srgbs = simulate_pipeline(input_srgbs, preset_key, custom_matrix=opt_mat)
        opt_labs = srgb_to_lab(opt_srgbs)
        opt_de_vals = delta_e_ciede2000(opt_labs, gt_labs)
        new_avg_de = float(np.mean(opt_de_vals))
        
        summary["optimized_matrix"] = opt_mat.tolist()
        summary["optimized_loss"] = round(new_avg_de, 2)
        summary["optimized_smali"] = format_smali_matrix(opt_mat)
        
    # 5. Generate figure if out_dir specified
    if out_dir:
        fig_path = generate_comparison_figure(preset_key, preset_name, patch_results, curve_1024, out_dir)
        summary["figure_rel_path"] = os.path.basename(fig_path)
        
    return summary

def evaluate_real_image(image_path, preset_key, ref_data):
    """
    Evaluates real-world captured image containing ColorChecker 24 chart against Ricoh GR III.
    Assumes image is either cropped to chart or samples 24 centers in a 4x6 grid.
    """
    from PIL import Image
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    
    # 4 rows x 6 columns grid sampling
    rows, cols = 4, 6
    sampled_srgbs = []
    
    for r in range(rows):
        for c in range(cols):
            # Center of patch with 10% inset box averaging to reject noise
            cx = int((c + 0.5) * (w / cols))
            cy = int((r + 0.5) * (h / rows))
            box_r = max(2, min(w, h) // 40)
            
            box = img.crop((cx - box_r, cy - box_r, cx + box_r, cy + box_r))
            mean_rgb = np.mean(np.array(box), axis=(0, 1))
            sampled_srgbs.append(mean_rgb)
            
    sampled_srgbs = np.array(sampled_srgbs, dtype=np.float64)
    ref_preset = ref_data["presets"].get(preset_key)
    gt_srgbs = np.array(ref_preset["ground_truth_srgb"], dtype=np.float64)
    
    sim_labs = srgb_to_lab(sampled_srgbs)
    gt_labs = srgb_to_lab(gt_srgbs)
    de_vals = delta_e_ciede2000(sim_labs, gt_labs)
    
    return sampled_srgbs, de_vals

def main():
    parser = argparse.ArgumentParser(description="Sony A6300 vs Ricoh GR III Color Science Benchmark")
    parser.add_argument("--preset", choices=list(PRESETS_CONFIG.keys()) + ["all"], default="all",
                        help="Target preset to evaluate (default: all)")
    parser.add_argument("--optimize", action="store_true", default=False,
                        help="Run closed-loop constrained optimization for 3x3 matrix")
    parser.add_argument("--html", action="store_true", default=True,
                        help="Generate interactive HTML report (default: True)")
    parser.add_argument("--out-dir", default=os.path.join(os.path.dirname(__file__), "reports"),
                        help="Output directory for generated reports and charts")
    parser.add_argument("--image", default=None,
                        help="Optional path to real A6300 photo containing 24-patch ColorChecker to benchmark real shots")
    args = parser.parse_args()
    
    os.makedirs(args.out_dir, exist_ok=True)
    ref_data = load_reference_data()
    
    if args.image:
        if args.preset == "all":
            print(f"{C_RED}Error: When using --image, please specify a single target preset using --preset <key>{C_RESET}")
            sys.exit(1)
        print(f"\n{C_BOLD}Analyzing real-world test image: {args.image}{C_RESET}")
        sampled, de_vals = evaluate_real_image(args.image, args.preset, ref_data)
        avg_de = np.mean(de_vals)
        print(f"Preset: {PRESETS_CONFIG[args.preset]['name']}")
        print(f"Measured Real Image Avg ΔE00: {avg_de:.2f}")
        print(f"Worst Patch ΔE00: {np.max(de_vals):.2f}")
        sys.exit(0)
        
    presets_to_run = list(PRESETS_CONFIG.keys()) if args.preset == "all" else [args.preset]
    
    print(f"\n{C_BOLD}{C_CYAN}========================================================================={C_RESET}")
    print(f"{C_BOLD}{C_CYAN}  Sony A6300 vs Ricoh GR III Color Science Verification & Benchmark  {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}========================================================================={C_RESET}\n")
    print(f"Reference Dataset: DPReview Studio Scene & Authentic Ricoh GR III Measurements")
    print(f"Standard Illuminant: D65 / X-Rite 24 ColorChecker")
    print(f"Evaluating Presets: {', '.join(presets_to_run)}")
    if args.optimize:
        print(f"Mode: {C_YELLOW}Active Optimization (Constrained SLSQP / L-BFGS-B){C_RESET}")
    print("-" * 73)
    
    summaries = []
    for key in presets_to_run:
        print(f"Evaluating preset [{key}] ...", end="", flush=True)
        s = run_preset_benchmark(key, ref_data, do_optimize=args.optimize, out_dir=args.out_dir)
        summaries.append(s)
        print(" DONE")
        
    # Print formatted terminal summary table
    print(f"\n{C_BOLD}SUMMARY BENCHMARK RESULTS:{C_RESET}\n")
    header = f"{'Preset Name':<32} {'Avg ΔE00':<10} {'Max ΔE00':<10} {'Black Pedestal':<16} {'Split (Δb*)':<12}"
    if args.optimize:
        header += f" {'Opt ΔE00':<10}"
    print(C_BOLD + header + C_RESET)
    print("-" * (len(header) + 2))
    
    for s in summaries:
        name = s["name"]
        avg_de = s["avg_delta_e00"]
        max_de = s["max_delta_e00"]
        black = f"{s['tone']['black_level_10bit']} (sRGB {s['tone']['black_pedestal_srgb']})"
        split_b = f"{s['gray_ramp']['split_toning_delta_b']:+.2f}"
        
        # Color coding for avg deltaE
        if avg_de <= 3.5:
            de_str = f"{C_GREEN}{avg_de:.2f} (Perceptual){C_RESET}"
        elif avg_de <= 5.5:
            de_str = f"{C_YELLOW}{avg_de:.2f} (Style Match){C_RESET}"
        else:
            de_str = f"{C_RED}{avg_de:.2f} (Deviation){C_RESET}"
            
        row = f"{name:<32} {de_str:<20} {max_de:<10.2f} {black:<16} {split_b:<12}"
        if args.optimize:
            opt_de = s["optimized_loss"]
            opt_str = f"{C_GREEN}{opt_de:.2f}{C_RESET}" if opt_de < avg_de else f"{opt_de:.2f}"
            row += f" {opt_str:<10}"
        print(row)
        
    print("-" * (len(header) + 2))
    print(f"{C_BOLD}Evaluation Scale:{C_RESET}")
    print(f"  • ΔE00 ≤ 3.0: Perceptually imperceptible difference (Master grade)")
    print(f"  • 3.0 < ΔE00 ≤ 6.0: Stylistic film simulation match (Accurate tone & rendition)")
    print(f"  • ΔE00 > 6.0: Noticeable tint or hue deviation\n")
    
    # Generate HTML Report
    if args.html:
        html_path = os.path.join(args.out_dir, "color_benchmark_report.html")
        generate_html_report(summaries, html_path)
        print(f"✓ Interactive HTML report generated: {C_CYAN}{html_path}{C_RESET}")
        
    if args.optimize:
        print(f"\n{C_BOLD}{C_YELLOW}⚡ OPTIMIZATION PROPOSALS FOR SMALI HOOKS:{C_RESET}")
        for s in summaries:
            if s["optimized_loss"] < s["avg_delta_e00"]:
                print(f"\nPreset: {C_BOLD}{s['name']}{C_RESET} ({s['key']})")
                print(f"  Avg ΔE00: {s['avg_delta_e00']:.2f} -> {C_GREEN}{s['optimized_loss']:.2f}{C_RESET} (Δ = -{s['avg_delta_e00'] - s['optimized_loss']:.2f})")
                print(f"  Recommended Matrix in RicohHook.smali:")
                print(s["optimized_smali"])

if __name__ == "__main__":
    main()
