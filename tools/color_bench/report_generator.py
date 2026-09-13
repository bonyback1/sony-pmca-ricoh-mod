# -*- coding: utf-8 -*-
"""
Report Generator for Color Benchmark:
Creates rich visual HTML reports, Markdown summaries, and Matplotlib comparison figures.
"""

import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti SC', 'DejaVu Sans', 'sans-serif']
matplotlib.rcParams['axes.unicode_minus'] = False
import matplotlib.pyplot as plt

def generate_comparison_figure(preset_key, preset_name, patch_results, curve_1024, output_dir):
    """
    Generates a 3-panel figure:
    1. ColorChecker 24-patch side-by-side swatch comparison
    2. Delta E 2000 per-patch bar chart with thresholds
    3. 1024-point tone transfer curve
    """
    os.makedirs(output_dir, exist_ok=True)
    fig_path = os.path.join(output_dir, f"{preset_key}_color_benchmark.png")
    
    fig = plt.figure(figsize=(16, 12), dpi=150)
    
    # 1. Delta E 2000 Bar Chart (Top Left)
    ax1 = fig.add_subplot(2, 2, 1)
    patch_ids = [p["id"] for p in patch_results]
    de_vals = [p["delta_e00"] for p in patch_results]
    colors = []
    for de in de_vals:
        if de <= 3.0:
            colors.append("#2ecc71") # green: excellent
        elif de <= 6.0:
            colors.append("#f39c12") # orange: good / acceptable
        else:
            colors.append("#e74c3c") # red: deviation
            
    bars = ax1.bar(patch_ids, de_vals, color=colors, edgecolor="#333", linewidth=0.8)
    ax1.axhline(y=3.0, color="#27ae60", linestyle="--", linewidth=1.2, label="Perceptual Match (ΔE ≤ 3.0)")
    ax1.axhline(y=6.0, color="#d35400", linestyle="--", linewidth=1.2, label="Style Match (ΔE ≤ 6.0)")
    ax1.set_xlabel("ColorChecker Patch ID (1..24)", fontsize=10)
    ax1.set_ylabel("CIEDE2000 Color Difference (ΔE00)", fontsize=10)
    ax1.set_title(f"Color Difference per Patch: {preset_name}", fontsize=12, fontweight="bold")
    ax1.set_xticks(range(1, 25))
    ax1.set_ylim(0, max(max(de_vals) * 1.15, 8.0))
    ax1.legend(loc="upper right", fontsize=9)
    ax1.grid(axis="y", alpha=0.3, linestyle=":")
    
    # 2. 1024-Point Tone Curve (Top Right)
    ax2 = fig.add_subplot(2, 2, 2)
    x_in = np.linspace(0, 1023, 1024)
    y_out = np.asarray(curve_1024)
    ax2.plot(x_in, y_out, color="#2980b9", linewidth=2.0, label="Filmic ExtendedGammaTable")
    ax2.plot([0, 1023], [0, 1023], color="#7f8c8d", linestyle=":", linewidth=1.0, label="Linear Identity (1:1)")
    ax2.fill_between(x_in, y_out, alpha=0.15, color="#3498db")
    ax2.set_xlabel("Input Sensor Code (10-bit: 0..1023)", fontsize=10)
    ax2.set_ylabel("Output Code (10-bit: 0..1023)", fontsize=10)
    ax2.set_title("10-bit Transfer Curve & Black Pedestal", fontsize=12, fontweight="bold")
    ax2.set_xlim(0, 1023)
    ax2.set_ylim(0, 1023)
    ax2.legend(loc="lower right", fontsize=9)
    ax2.grid(alpha=0.3, linestyle=":")
    
    # Annotate black pedestal and mid point
    ax2.annotate(f"Black Floor: {y_out[0]}", xy=(0, y_out[0]), xytext=(60, y_out[0] + 80),
                 arrowprops=dict(facecolor="#e74c3c", shrink=0.08, width=1, headwidth=6),
                 fontsize=9, fontweight="bold", color="#c0392b")
    ax2.annotate(f"Mid (512): {y_out[512]}", xy=(512, y_out[512]), xytext=(400, y_out[512] + 120),
                 arrowprops=dict(facecolor="#2980b9", shrink=0.08, width=1, headwidth=6),
                 fontsize=9, fontweight="bold", color="#2980b9")

    # 3. 24-Patch Visual Comparison Grid (Bottom, spanning 2 columns)
    ax3 = fig.add_subplot(2, 1, 2)
    ax3.set_title("X-Rite 24 ColorChecker Comparison: [Top: Simulated A6300 / Bottom: Ricoh GR III Ground Truth]",
                  fontsize=12, fontweight="bold", pad=12)
    
    # Draw 4 rows x 6 cols of split patches
    cols = 6
    rows = 4
    for idx, p in enumerate(patch_results):
        r = idx // cols
        c = idx % cols
        
        sim_rgb = np.array(p["simulated_srgb"]) / 255.0
        gt_rgb = np.array(p["ground_truth_srgb"]) / 255.0
        
        # Top half: Simulated A6300
        rect_top = plt.Rectangle((c * 1.1, (3 - r) * 1.1 + 0.5), 1.0, 0.5, facecolor=sim_rgb, edgecolor="none")
        ax3.add_patch(rect_top)
        
        # Bottom half: Ricoh GR3 Ground Truth
        rect_bot = plt.Rectangle((c * 1.1, (3 - r) * 1.1), 1.0, 0.5, facecolor=gt_rgb, edgecolor="none")
        ax3.add_patch(rect_bot)
        
        # Border
        rect_border = plt.Rectangle((c * 1.1, (3 - r) * 1.1), 1.0, 1.0, facecolor="none", edgecolor="#222", linewidth=1.2)
        ax3.add_patch(rect_border)
        
        # Label with ID and deltaE
        ax3.text(c * 1.1 + 0.5, (3 - r) * 1.1 + 0.5, f"#{p['id']}\nΔE:{p['delta_e00']:.1f}",
                 ha="center", va="center", fontsize=8, fontweight="bold",
                 color="white" if np.mean(sim_rgb) < 0.5 else "black",
                 bbox=dict(boxstyle="round,pad=0.2", facecolor="black" if np.mean(sim_rgb) > 0.5 else "white", alpha=0.5, edgecolor="none"))

    ax3.set_xlim(-0.1, cols * 1.1)
    ax3.set_ylim(-0.1, rows * 1.1)
    ax3.set_aspect("equal")
    ax3.axis("off")
    
    plt.tight_layout()
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig_path

def generate_html_report(all_preset_summaries, output_path):
    """
    Generates a modern, interactive HTML report containing all benchmark metrics,
    swatches, tone curve properties, and auto-tuning recommendations.
    """
    lines = []
    lines.append("<!DOCTYPE html>")
    lines.append("<html lang=\"en\">")
    lines.append("<head>")
    lines.append("<meta charset=\"UTF-8\">")
    lines.append("<title>Sony A6300 vs Ricoh GR III Color Science Benchmark</title>")
    lines.append("<style>")
    lines.append("  body { font-family: -apple-system, BlinkMacSystemFont, \x27Segoe UI\x27, Roboto, Helvetica, Arial, sans-serif; background: #0f141c; color: #e1e7ec; margin: 0; padding: 24px; }")
    lines.append("  .container { max-width: 1200px; margin: 0 auto; }")
    lines.append("  h1 { color: #f39c12; font-size: 28px; margin-bottom: 8px; }")
    lines.append("  .subhead { color: #8892b0; margin-bottom: 32px; font-size: 15px; }")
    lines.append("  .card { background: #1a2230; border-radius: 10px; border: 1px solid #2d3b4e; padding: 24px; margin-bottom: 32px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }")
    lines.append("  .card h2 { color: #64ffda; margin-top: 0; font-size: 20px; border-bottom: 1px solid #2d3b4e; padding-bottom: 12px; }")
    lines.append("  .metric-row { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }")
    lines.append("  .metric-box { background: #131924; border: 1px solid #2d3b4e; border-radius: 8px; padding: 14px 20px; flex: 1; min-width: 160px; }")
    lines.append("  .metric-title { font-size: 12px; color: #8892b0; text-transform: uppercase; margin-bottom: 4px; }")
    lines.append("  .metric-val { font-size: 24px; font-weight: bold; }")
    lines.append("  .val-pass { color: #2ecc71; }")
    lines.append("  .val-warn { color: #f39c12; }")
    lines.append("  .val-fail { color: #e74c3c; }")
    lines.append("  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; }")
    lines.append("  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #2d3b4e; }")
    lines.append("  th { background: #131924; color: #8892b0; font-weight: 600; }")
    lines.append("  .swatch { display: inline-block; width: 32px; height: 20px; border-radius: 4px; vertical-align: middle; border: 1px solid #444; margin-right: 6px; }")
    lines.append("  .img-container { text-align: center; margin: 24px 0; }")
    lines.append("  .img-container img { max-width: 100%; border-radius: 8px; border: 1px solid #2d3b4e; }")
    lines.append("  pre { background: #131924; border: 1px solid #2d3b4e; border-radius: 6px; padding: 14px; font-family: \x27SF Mono\x27, Consolas, Menlo, monospace; font-size: 12px; color: #64ffda; overflow-x: auto; }")
    lines.append("</style>")
    lines.append("</head>")
    lines.append("<body>")
    lines.append("<div class=\"container\">")
    lines.append("  <h1>📷 Sony A6300 vs Ricoh GR III Color Science Benchmark</h1>")
    lines.append("  <div class=\"subhead\">Universal PMCA Ricoh Camera Mod (v1.4.0 / B2.2) • Ground Truth Comparison & Closed-Loop Calibration Report</div>")

    for s in all_preset_summaries:
        p_key = s["key"]
        p_name = s["name"]
        avg_de = s["avg_delta_e00"]
        max_de = s["max_delta_e00"]
        de_class = "val-pass" if avg_de <= 4.0 else ("val-warn" if avg_de <= 7.0 else "val-fail")
        
        lines.append("  <div class=\"card\">")
        lines.append(f"    <h2>{p_name}</h2>")
        lines.append("    <div class=\"metric-row\">")
        lines.append("      <div class=\"metric-box\">")
        lines.append("        <div class=\"metric-title\">Average ΔE₀₀</div>")
        lines.append(f"        <div class=\"metric-val {de_class}\">{avg_de:.2f}</div>")
        lines.append("      </div>")
        lines.append("      <div class=\"metric-box\">")
        lines.append("        <div class=\"metric-title\">Max ΔE₀₀ (Worst Patch)</div>")
        lines.append(f"        <div class=\"metric-val\">{max_de:.2f}</div>")
        lines.append("      </div>")
        lines.append("      <div class=\"metric-box\">")
        lines.append("        <div class=\"metric-title\">Black Pedestal (10-bit)</div>")
        lines.append(f"        <div class=\"metric-val\">{s['tone']['black_level_10bit']} <span style=\"font-size:13px;color:#8892b0;\">({s['tone']['black_pedestal_srgb']} sRGB)</span></div>")
        lines.append("      </div>")
        lines.append("      <div class=\"metric-box\">")
        lines.append("        <div class=\"metric-title\">Split Toning (Δb*)</div>")
        lines.append(f"        <div class=\"metric-val\">{s['gray_ramp']['split_toning_delta_b']:+.2f}</div>")
        lines.append("      </div>")
        lines.append("    </div>")
        
        if s.get("figure_rel_path"):
            lines.append("    <div class=\"img-container\">")
            lines.append(f"      <img src=\"{s['figure_rel_path']}\" alt=\"{p_name} Benchmark Chart\" />")
            lines.append("    </div>")
            
        if s.get("optimized_matrix") is not None:
            lines.append("    <h3 style=\"color:#f39c12;font-size:16px;margin-top:20px;\">⚡ Closed-Loop Optimized Matrix Proposal:</h3>")
            lines.append(f"    <p style=\"font-size:13px;color:#8892b0;\">Reduces Average ΔE₀₀ from <b>{avg_de:.2f}</b> to <b>{s['optimized_loss']:.2f}</b></p>")
            lines.append(f"    <pre>{s['optimized_smali']}</pre>")
            
        lines.append("  </div>")

    lines.append("</div>")
    lines.append("</body>")
    lines.append("</html>")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return output_path
