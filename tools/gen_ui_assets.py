#!/usr/bin/env python3
"""Generate the Ricoh Camera menu icons and preview images.

Output goes to src/icons/, using the exact original Sony resource names.
tools/patch_apk.py (patch_menu_icons) then copies these files over the
originals.

* Menu icons (70x60): the lettering is rebuilt on a clean palette template.
  The template is derived from all 13 official icons by taking the per-pixel
  mode and keeping only high-agreement rim pixels. The lettering uses Avenir
  Next Condensed Heavy, calibrated against Sony's own lettering (IoU ~0.68),
  and is encoded the way Sony encodes it: grey 221 fill, a black halo, and
  4-bit (x17) quantisation.
* Preview images (280x480): a source photo is run through the shipped
  Gamma + RGB-matrix pipeline. The 10-bit gamma tables and Q10 matrices are
  parsed straight from src/smali/RicohHook.smali. The result is then baked the
  way Sony's samples are: dimmed to a maximum of 85, darkened by left and top
  ramps, and dithered to 6 levels.

Usage:  python3 tools/gen_ui_assets.py [--source photo.jpg] [--sheet out.png]
"""
import argparse, glob, os, re
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'decompiled/Sony_A6300_pictureeffectplus/res/drawable-notlong-nodpi-v4')
OUT = os.path.join(ROOT, 'src/icons')
SMALI = os.path.join(ROOT, 'src/smali/RicohHook.smali')
FONT = ('/System/Library/Fonts/Avenir Next Condensed.ttc', 2)   # Demi Bold (visual match to Sony weight)
ICON = 'p_16_dd_parts_pe_menu_icon_normal_%s.png'
IMAGE = 'p_16_dd_parts_pe_image_%s.png'

# resource suffix -> (label lines | official icon to copy, smali preset key, LB shift)
SLOTS = [
    ('pop_color',          {'copy': 'posterization'},      'pos',   0),
    ('retro',              {'lines': ['Neg']},             'neg',   2),
    ('rich_tone_mono',     {'copy': 'high_contrast_mono'}, 'hcbw',  0),
    ('high_contrast_mono', {'lines': ['Daido']},           'daido', 0),
    ('watercolor',         {'lines': ['Steve', 'McCurry']}, 'xpro', 0),
]

# ----------------------------------------------------------------- template
def load_icons():
    return {f.split('normal_')[1][:-4]: np.array(Image.open(f).convert('RGBA'))
            for f in sorted(glob.glob(os.path.join(RES, ICON % '*')))}

def clean_template(icons):
    stack = np.stack(list(icons.values()))
    n, H, W, _ = stack.shape
    tmpl = np.zeros((H, W, 4), np.uint8); conf = np.zeros((H, W), int)
    for y in range(H):
        for x in range(W):
            v, c = Counter(tuple(p) for p in stack[:, y, x]).most_common(1)[0]
            tmpl[y, x] = v; conf[y, x] = c
    core = (conf >= 8) & (tmpl[..., 3] > 0)
    keep = ndimage.binary_dilation(core, iterations=1)
    tmpl[~keep] = 0
    # drop stray specks (e.g. the shared first-letter stem pixels); keep the rim
    lab, n = ndimage.label(tmpl[..., 3] > 0, structure=np.ones((3, 3)))
    if n > 1:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        tmpl[lab != 1 + int(np.argmax(sizes))] = 0
    return tmpl

# ----------------------------------------------------------------- lettering
SS_SIZE = 224          # render size (28 px * 8x supersampling, as calibrated)
STROKE = 0             # faux-bold at 8x (0 = none)

def _glyphs(text, stroke):
    f = ImageFont.truetype(FONT[0], SS_SIZE, index=FONT[1])
    cap = f.getbbox('H')                       # (x0, top, x1, baseline)
    widths = [f.getlength(ch) for ch in text]
    track = -8                                 # -1 px at 8x
    W = int(sum(widths) + track * (len(text) - 1)) + 64
    canvas = Image.new('L', (W, SS_SIZE * 2), 0)
    d = ImageDraw.Draw(canvas); x = 32
    for ch, w in zip(text, widths):
        d.text((x, 0), ch, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
        x += w + track
    cols = np.where(np.array(canvas).max(0) > 0)[0]
    top, base = cap[1] - stroke, cap[3] + stroke
    return canvas.crop((cols[0], top, cols[-1] + 1, SS_SIZE * 2)), base - top

def render_label(text, cap_px, max_w, sx=0.68, min_sx=0.56):
    """Return a float alpha array whose row 0 is the cap top.

    The text is first condensed (down to min_sx) to fit max_w. If it still
    does not fit, the cap height is shrunk, as Sony does for 'WtrC'.
    """
    stroke = STROKE
    img, cap_ss = _glyphs(text, stroke)
    while True:
        v = cap_px / cap_ss
        w = img.width * v * sx
        if w <= max_w + 0.01: break
        if sx > min_sx: sx = max(min_sx, sx * max_w / w); continue
        cap_px -= 0.5
    out = img.resize((max(1, round(img.width * v * sx)), max(1, round(img.height * v))), Image.LANCZOS)
    a = np.array(out).astype(float) / 255
    rows = np.where(a.max(1) > 0.05)[0]
    return a[:rows[-1] + 1], cap_px

def compose_icon(tmpl, lines):
    H, W = tmpl.shape[:2]
    text = np.zeros((H, W))
    def place(a, x0, y0):
        h, w = a.shape
        text[y0:y0 + h, x0:x0 + w] = np.maximum(text[y0:y0 + h, x0:x0 + w], a[:H - y0, :W - x0])
    if len(lines) == 1:
        a, cap = render_label(lines[0], 21, 31)
        y0 = round(17 + (22 - cap) / 2)        # keep the optical centre at y~28
        place(a, 22, y0)
    else:
        boxes = [(13, 16, 37, 30), (31, 13, 36, 25)]   # (top, cap, centre x, max width)
        for txt, (top, cap, cx, mw) in zip(lines, boxes):
            a, c = render_label(txt, cap, mw)
            place(a, int(round(cx - a.shape[1] / 2)), int(round(top + (cap - c) / 2)))
    text = np.clip(text, 0, 1)
    # black halo: blurred, dilated copy of the lettering
    halo = ndimage.gaussian_filter(ndimage.grey_dilation(text, size=3), 0.7) * 0.8
    base = tmpl.astype(float) / 255
    def over(dst, rgb, a):
        out_a = a + dst[..., 3] * (1 - a)
        out_rgb = (np.array(rgb)[None, None] * a[..., None] +
                   dst[..., :3] * dst[..., 3:] * (1 - a[..., None])) / np.maximum(out_a[..., None], 1e-6)
        return np.dstack([out_rgb, out_a])
    img = over(base, (0, 0, 0), np.clip(halo, 0, 1))
    img = over(img, (221 / 255,) * 3, text)
    q = (np.round(img * 15) * 17).astype(np.uint8)
    q[q[..., 3] == 0] = 0
    return q

# ----------------------------------------------------------------- pipeline
def parse_smali():
    s = open(SMALI, encoding='utf-8').read()
    def block(label):
        m = re.search(r':%s\s*\n\s*\.array-data \d+\s*\n(.*?)\.end array-data' % label, s, re.S)
        return [int(t.rstrip('t'), 16) for t in m.group(1).split()]
    params = {}
    for k in ('pos', 'neg', 'hcbw', 'daido', 'xpro'):
        mat = np.array(block('array_%s_matrix' % k), float).reshape(3, 3) / 1024
        b = np.array(block('array_gamma_%s' % k)) & 0xFF
        gamma = (b[0::2] | (b[1::2] << 8)).astype(float)
        params[k] = (gamma, mat)
    return params

def apply_pipeline(rgb, gamma, mat, lb):
    idx = np.linspace(0, 1023, 1024)
    x = np.interp(rgb / 255 * 1023, idx, gamma) / 1023 * 255
    x[..., 0] *= 1 + 0.025 * lb; x[..., 2] *= 1 - 0.025 * lb
    return np.clip(x @ mat.T, 0, 255)

def bake_preview(rgb):
    """Imitate Sony's sample bake: max 85, left/top fades, 6-level dither."""
    H, W = rgb.shape[:2]
    sm = lambda t: t * t * (3 - 2 * t)
    left = sm(np.clip(np.arange(W) / 120, 0, 1))
    top = 0.35 + 0.65 * sm(np.clip(np.arange(H) / 170, 0, 1))
    img = rgb / 255 * 85 * left[None, :, None] * top[:, None, None] / 17  # 0..5
    out = np.zeros_like(img)
    for y in range(H):                       # Floyd-Steinberg per channel
        for x in range(W):
            o = img[y, x]; q = np.clip(np.round(o), 0, 5); out[y, x] = q; e = o - q
            if x + 1 < W: img[y, x + 1] += e * 7 / 16
            if y + 1 < H:
                if x: img[y + 1, x - 1] += e * 3 / 16
                img[y + 1, x] += e * 5 / 16
                if x + 1 < W: img[y + 1, x + 1] += e / 16
    q = (out * 17).astype(np.uint8)
    im = Image.fromarray(q, 'RGB')
    cols = sorted({tuple(c) for c in q.reshape(-1, 3)})
    pal = Image.new('P', (1, 1)); pal.putpalette([v for c in cols for v in c] + [0] * 3 * (256 - len(cols)))
    return im.quantize(palette=pal, dither=Image.Dither.NONE)

def load_source(path):
    im = Image.open(path).convert('RGB')
    s = max(280 / im.width, 480 / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x0 = im.width - 280 - (im.width - 280) // 4   # bias subject to the right (left side fades)
    y0 = (im.height - 480) // 2
    return np.array(im.crop((x0, y0, x0 + 280, y0 + 480))).astype(float)

# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    import matplotlib
    default_src = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data/sample_data/grace_hopper.jpg')
    ap.add_argument('--source', default=default_src)
    ap.add_argument('--sheet', help='write an x4 contact sheet here')
    ap.add_argument('--no-images', action='store_true')
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    icons = load_icons(); tmpl = clean_template(icons)
    params = parse_smali(); src = load_source(a.source)
    made_icons, made_imgs = [], []
    for res, spec, key, lb in SLOTS:
        if 'copy' in spec:
            ic = icons[spec['copy']]
        else:
            ic = compose_icon(tmpl, spec['lines'])
        Image.fromarray(ic, 'RGBA').save(os.path.join(OUT, ICON % res), optimize=True)
        made_icons.append(ic)
        if not a.no_images:
            gamma, mat = params[key]
            pv = bake_preview(apply_pipeline(src, gamma, mat, lb))
            pv.save(os.path.join(OUT, IMAGE % res), optimize=True)
            made_imgs.append(pv)
        print('wrote', res)
    if a.sheet:
        k = 4; cell = 70 * k
        sheet = Image.new('RGB', (cell * 5, 60 * k * 2 + (480 if made_imgs else 0)), (0, 0, 0))
        for i, (res, *_r) in enumerate(SLOTS):
            old = Image.open(os.path.join(RES, ICON % res)).convert('RGBA').resize((cell, 60 * k), Image.NEAREST)
            new = Image.fromarray(made_icons[i]).resize((cell, 60 * k), Image.NEAREST)
            sheet.paste(old, (i * cell, 0), old); sheet.paste(new, (i * cell, 60 * k), new)
            if made_imgs:
                pv = made_imgs[i].convert('RGB').point(lambda v: min(255, v * 3))
                sheet.paste(pv, (i * cell, 120 * k))
        sheet.save(a.sheet)

if __name__ == '__main__':
    main()
