"""
Geetha Jewellers - collection stage asset build (separate display assets)
------------------------------------------------------------------------
    python tools/build_assets.py

Inputs (project root)
    white hero bacKground 2.PNG          environment (header baked in)
    Necklaces.PNG                        isolated NECKLACES display, RGBA
    rings earrings.PNG                   RINGS + EARRINGS displays on a fake checkerboard
    bangles diamond pendant sets.PNG     BANGLES + DIAMOND PENDANT SETS displays on a fake checkerboard

Outputs (images/)
    bg-stage.webp / .jpg     environment with the nav / logo removed from the header band
    logo.webp / .png         transparent gold logo
    necklace | ring | earrings | bangles | pendant-set  .webp / .png
                             one complete display each: glass dome, gold frame, pedestal with its
                             engraved name, jewellery - used exactly as supplied, native resolution
    manifest.json            jewellery boxes (fractions of each image) for the light sweep

What is done to the supplied displays (and nothing else):
  * the two pair images are split into their two displays and unmixed from the
    baked checkerboard (the generator's "transparency" pattern) so they become
    real transparent objects;
  * the open glass inside every dome is made see-through (the pairs by the
    unmixing, the necklace by keying its near-white interior), keeping the gold
    frame, the glass highlights, jewellery, display forms and pedestals as they are.
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
SRC_BG = os.path.join(ROOT, "white hero bacKground 2.PNG")
SRC_NECKLACE = os.path.join(ROOT, "Necklaces.PNG")
SRC_PAIR_RE = os.path.join(ROOT, "rings earrings.PNG")
SRC_PAIR_BP = os.path.join(ROOT, "bangles diamond pendant sets.PNG")

WEBP_QUALITY = 90
MAX_HEIGHT = 1214          # keep native resolution (the tallest supplied asset)


# ------------------------------------------------------------------ helpers
def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0


def load_rgba(path):
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.float32) / 255.0


def u8(a):
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def feather(m, sigma):
    return np.clip(cv2.GaussianBlur(m, (0, 0), sigma), 0.0, 1.0) if sigma > 0 else m


def kernel(n):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (n, n))


def rect(h, w, box):
    x0, y0, x1, y1 = box
    m = np.zeros((h, w), np.float32)
    m[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = 1.0
    return m


def ellipse(h, w, cx, cy, rx, ry, upper_only=False, lower_only=False):
    ys, xs = np.mgrid[0:h, 0:w]
    m = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1.0
    if upper_only:
        m &= ys <= cy
    if lower_only:
        m &= ys >= cy
    return m.astype(np.float32)


def poly(h, w, pts):
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 255)
    return m.astype(np.float32) / 255.0


def dome(h, w, box, arc_h):
    """Cloche silhouette: elliptical top of height arc_h on a rectangle."""
    x0, y0, x1, y1 = box
    cx, rx, cy = (x0 + x1) / 2.0, (x1 - x0) / 2.0, y0 + arc_h
    return np.maximum(rect(h, w, (x0, int(round(cy)), x1, y1)), ellipse(h, w, cx, cy, rx, arc_h, upper_only=True))


def cylinder(h, w, spec):
    """Upright cylinder seen from slightly above: (x0, y_top, x1, y_bottom, ry_top, ry_bottom)."""
    x0, yt, x1, yb, rt, rb = spec
    cx, rx = (x0 + x1) / 2.0, (x1 - x0) / 2.0
    m = rect(h, w, (x0, yt, x1, yb))
    m = np.maximum(m, ellipse(h, w, cx, yt, rx, rt, upper_only=True))
    return np.maximum(m, ellipse(h, w, cx, yb, rx, rb, lower_only=True))


def inpaint(rgb, mask, radius=8):
    out = cv2.inpaint(u8(rgb), (mask > 0.5).astype(np.uint8) * 255, radius, cv2.INPAINT_TELEA)
    return out.astype(np.float32) / 255.0


def box_mean(values, weights, size):
    """Weighted box average: sum(values*weights) / sum(weights) over a size x size window."""
    num = cv2.boxFilter(values * weights, -1, (size, size), normalize=False)
    den = cv2.boxFilter(weights, -1, (size, size), normalize=False)
    return num / np.maximum(den, 1e-6), den


def fill_holes(binary):
    contours, _ = cv2.findContours(binary.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(binary, dtype=np.uint8)
    cv2.drawContours(filled, [c for c in contours if cv2.contourArea(c) > 120], -1, 1, thickness=cv2.FILLED)
    return filled.astype(np.float32)


def save_rgba(rgb, alpha, name):
    """Crop to the alpha bbox, write WebP + PNG at native resolution. Returns the bbox."""
    ys, xs = np.where(alpha > 0.01)
    pad = 4
    y0, y1 = max(0, ys.min() - pad), min(alpha.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(alpha.shape[1], xs.max() + pad + 1)
    rgb, alpha = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
    out = np.clip(rgb, 0, 1).copy()
    out[alpha < 0.002] = 1.0
    im = Image.fromarray(np.dstack([u8(out), u8(alpha)]), "RGBA")
    if im.size[1] > MAX_HEIGHT:
        im = im.resize((round(im.size[0] * MAX_HEIGHT / im.size[1]), MAX_HEIGHT), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=WEBP_QUALITY, method=6, exact=False)
    im.save(os.path.join(OUT, f"{name}.png"), "PNG", optimize=True)
    print(f"  {name:14s} {im.size[0]}x{im.size[1]}")
    return (x0, y0, x1, y1)


# ------------------------------------------------------------------ environment + logo (reference A)
NAV_BOXES = [(60, 56, 130, 96), (178, 56, 306, 90), (352, 56, 452, 90),
             (1140, 56, 1236, 90), (1266, 56, 1340, 90), (1368, 56, 1520, 90),
             (1576, 58, 1626, 92), (0, 110, 668, 126), (1004, 110, 1672, 126)]
LOGO_BOX = (700, 0, 975, 152)
EMBLEM = (836, 48, 44, 50)              # cx, cy, rx, ry  (reference A)
LOGO_ROWS = [(716, 92, 958, 122), (748, 122, 926, 142)]


def ink_mask(rgb, boxes, dark=0.66, gold=0.10, dilate=7):
    h, w, _ = rgb.shape
    m = np.zeros((h, w), np.float32)
    lum = rgb.mean(axis=2)
    warm = rgb[..., 0] - rgb[..., 2]
    for (x0, y0, x1, y1) in boxes:
        sub = (lum[y0:y1, x0:x1] < dark) | (warm[y0:y1, x0:x1] > gold)
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], sub.astype(np.float32))
    return cv2.dilate(m, kernel(dilate))


def build_environment(bg):
    print("environment:")
    h, w, _ = bg.shape
    mask = np.maximum(ink_mask(bg, NAV_BOXES), rect(h, w, LOGO_BOX))
    clean = inpaint(bg, mask, radius=9)
    im = Image.fromarray(u8(clean), "RGB")
    im.save(os.path.join(OUT, "bg-stage.webp"), "WEBP", quality=86, method=6)
    im.save(os.path.join(OUT, "bg-stage.jpg"), "JPEG", quality=88, optimize=True, progressive=True)
    print(f"  bg-stage       {im.size[0]}x{im.size[1]}")


def build_logo(bg):
    print("logo:")
    x0, y0, x1, y1 = LOGO_BOX
    pad = 48
    big = bg[max(0, y0 - pad):y1 + pad, x0 - pad:x1 + pad]
    hole = np.zeros(big.shape[:2], np.float32)
    oy = y0 - max(0, y0 - pad)
    hole[oy:oy + (y1 - y0), pad:pad + (x1 - x0)] = 1.0
    behind = inpaint(big, hole, radius=16)[oy:oy + (y1 - y0), pad:pad + (x1 - x0)]
    crop = bg[y0:y1, x0:x1]
    hh, ww, _ = crop.shape
    diff = cv2.GaussianBlur(np.abs(crop - behind).max(axis=2), (0, 0), 0.6)
    key = smoothstep(0.05, 0.28, diff)
    cx, cy, rx, ry = EMBLEM
    emblem = ellipse(hh, ww, cx - x0, cy - y0, rx, ry)
    region = ellipse(hh, ww, cx - x0, cy - y0, rx + 4, ry + 4)
    for (rx0, ry0, rx1, ry1) in LOGO_ROWS:
        region = np.maximum(region, rect(hh, ww, (rx0 - x0, ry0 - y0, rx1 - x0, ry1 - y0)))
    coverage = np.maximum(key * feather(region, 1.5), feather(emblem, 1.0))
    colour = np.clip((crop - (1 - coverage)[..., None] * behind) / np.maximum(coverage, 1e-3)[..., None], 0, 1)
    save_rgba(colour, coverage, "logo")


# ------------------------------------------------------------------ display geometry
# Coordinates are pixels in each display's own source image (the pairs use the pair image's
# coordinates; `crop` is the horizontal split).
NECKLACE = dict(
    name="necklace",
    dome=(240, 10, 1056, 935), arc=245,
    solids=[("cyl", (232, 910, 1064, 932, 10, 10)),        # gold ring at the dome base
            ("cyl", (300, 878, 1000, 942, 18, 10)),        # inner white marble disc
            ("cyl", (176, 962, 1122, 1148, 30, 24))],      # pedestal with NECKLACES
    jewel=(360, 380, 930, 900),
)

PAIR_LEFT = dict(dome=(66, 10, 694, 800), arc=225,
                 solids=[("cyl", (52, 782, 708, 802, 8, 8)),        # gold ring at the dome base
                         ("cyl", (178, 726, 582, 802, 16, 8)),      # inner white disc
                         ("cyl", (118, 812, 642, 916, 14, 12)),     # pedestal with the name
                         ("cyl", (2, 918, 760, 968, 12, 18)),       # gold plate
                         ("rect", (180, 335, 580, 730)), ("ell", (380, 335, 200, 105))],   # velvet panel
                 crop=(0, 768))
PAIR_RIGHT = dict(dome=(836, 10, 1464, 800), arc=225,
                  solids=[("cyl", (822, 782, 1478, 802, 8, 8)),
                          ("cyl", (948, 726, 1352, 802, 16, 8)),
                          ("cyl", (888, 812, 1412, 916, 14, 12)),
                          ("cyl", (776, 918, 1534, 968, 12, 18)),
                          ("rect", (950, 335, 1350, 730)), ("ell", (1150, 335, 200, 105))],
                  crop=(768, 1536))

PAIRS = [
    (SRC_PAIR_RE, [dict(PAIR_LEFT, name="ring", jewel=(215, 360, 550, 645)),
                   dict(PAIR_RIGHT, name="earrings", jewel=(980, 320, 1320, 665))]),
    (SRC_PAIR_BP, [dict(PAIR_LEFT, name="bangles", jewel=(175, 290, 565, 690)),
                   dict(PAIR_RIGHT, name="pendant-set", jewel=(955, 255, 1345, 705))]),
]


def solid_mask(h, w, parts):
    m = np.zeros((h, w), np.float32)
    for kind, spec in parts:
        if kind == "cyl":
            m = np.maximum(m, cylinder(h, w, spec))
        elif kind == "rect":
            m = np.maximum(m, rect(h, w, spec))
        elif kind == "ell":
            m = np.maximum(m, ellipse(h, w, *spec, upper_only=True))
        else:
            m = np.maximum(m, poly(h, w, spec))
    return m


def jewel_fill(object_mask, jbox):
    """Everything object-like inside the jewel box, closed and hole-filled: the jewellery."""
    jew = ((object_mask > 0.5) & (jbox > 0.5)).astype(np.uint8)
    jew = cv2.morphologyEx(jew, cv2.MORPH_CLOSE, kernel(15))
    return feather(fill_holes(jew), 1.2)


def gold_key(rgb):
    lum = rgb.mean(axis=2)
    return smoothstep(0.10, 0.22, rgb[..., 0] - rgb[..., 2]) * smoothstep(0.95, 0.85, lum)


def save_glints(rgb, alpha, bbox, jewel, name):
    """Mask of the stones / speculars inside the jewel box (white = catches the light).

    Bright, low-saturation, opaque pixels - the diamonds and the sharpest gold
    highlights - slightly dilated so each stone blooms as the light passes."""
    bx0, by0, bx1, by1 = bbox
    sub, a = rgb[by0:by1, bx0:bx1], alpha[by0:by1, bx0:bx1]
    h, w = a.shape
    jx0, jy0, jx1, jy1 = jewel
    jbox = rect(h, w, (jx0 - bx0, jy0 - by0, jx1 - bx0, jy1 - by0))
    mn, mx = sub.min(axis=2), sub.max(axis=2)
    bright = smoothstep(0.84, 0.95, sub.mean(axis=2)) * smoothstep(0.24, 0.10, mx - mn)
    m = bright * (a > 0.9) * jbox
    m = cv2.dilate(m, kernel(3))
    m = feather(m, 0.8)
    im = Image.fromarray(u8(m), "L")
    if im.size[1] > MAX_HEIGHT:
        im = im.resize((round(im.size[0] * MAX_HEIGHT / im.size[1]), MAX_HEIGHT), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}-glints.png"), "PNG", optimize=True)
    return f"images/{name}-glints.png"


def record(manifest, d, bbox, glints):
    bx0, by0, bx1, by1 = bbox
    jx0, jy0, jx1, jy1 = d["jewel"]
    bw, bh = bx1 - bx0, by1 - by0
    manifest[d["name"]] = {
        "image": f"images/{d['name']}.webp",
        "glints": glints,
        "jewel": [round((jx0 - bx0) / bw, 4), round((jy0 - by0) / bh, 4),
                  round((jx1 - jx0) / bw, 4), round((jy1 - jy0) / bh, 4)],
    }


# ------------------------------------------------------------------ necklace (RGBA supplied)
def build_necklace(manifest):
    rgba = load_rgba(SRC_NECKLACE)
    rgb, a0 = rgba[..., :3], rgba[..., 3]
    h, w = a0.shape
    d = NECKLACE
    sil = dome(h, w, d["dome"], d["arc"])
    solid = solid_mask(h, w, d["solids"])
    rim = sil - cv2.erode(sil, kernel(41))                       # dome frame band (~20px)
    jbox = rect(h, w, d["jewel"])
    interior = np.clip(sil - np.maximum(solid, rim), 0, 1)

    # what is glass inside the dome: near-white, low-saturation pixels
    mn, mx = rgb.min(axis=2), rgb.max(axis=2)
    whiteness = smoothstep(0.74, 0.94, mn) * smoothstep(0.16, 0.05, mx - mn)
    glass = feather(whiteness * interior, 1.0)
    # the jewellery box: anything not glass, closed and filled (keeps the white diamonds)
    jew = jewel_fill(1.0 - glass, jbox)
    coverage = np.clip(1.0 - glass, 0, 1)
    coverage = np.maximum(coverage, np.maximum(feather(solid, 1.5), jew))
    coverage = np.maximum(coverage, gold_key(rgb) * rim)
    # un-premultiply the see-through glass against the white it was rendered on
    colour = np.clip((rgb - (1 - coverage)[..., None] * 1.0) / np.maximum(coverage, 1e-3)[..., None], 0, 1)
    colour = np.where(coverage[..., None] > 0.98, rgb, colour)
    alpha = a0 * coverage
    bbox = save_rgba(colour, alpha, d["name"])
    record(manifest, d, bbox, save_glints(colour, alpha, bbox, d["jewel"], d["name"]))


# ------------------------------------------------------------------ pairs (checkerboard supplied)
def checker_levels(rgb):
    """The two grey levels of the baked checkerboard, from the top-left corner."""
    g = rgb[4:60, 4:60].mean(axis=2).flatten()
    lo, hi = np.percentile(g, 20), np.percentile(g, 80)
    return float(g[g < (lo + hi) / 2].mean()), float(g[g > (lo + hi) / 2].mean())


def unmix_checker(rgb, glass_or_bg, D, L, window=19):
    """Per-pixel alpha / colour of a translucent layer over a known-contrast checkerboard.

    In a window covering both square phases the layer is ~constant, so the observed
    contrast between light and dark squares is (1 - alpha) * (L - D).
    """
    g = rgb.mean(axis=2)
    cand = glass_or_bg.astype(np.float32)
    local_mean, _ = box_mean(g, cand, window)
    light = ((g > local_mean) & (cand > 0.5)).astype(np.float32)
    dark = ((g <= local_mean) & (cand > 0.5)).astype(np.float32)
    o_l, n_l = box_mean(g, light, window)
    o_d, n_d = box_mean(g, dark, window)
    ok = (n_l > 6) & (n_d > 6)
    alpha = 1.0 - np.clip((o_l - o_d) / (L - D), 0.0, 1.0)
    alpha = np.where(ok, alpha, 1.0)
    c = np.where(g > local_mean, L, D)[..., None]
    colour = (rgb - (1 - alpha)[..., None] * c) / np.maximum(alpha, 1e-3)[..., None]
    return alpha, np.clip(colour, 0, 1)


def build_pair(src, specs, manifest):
    rgb = load_rgb(src)
    h, w, _ = rgb.shape
    D, L = checker_levels(rgb)
    for d in specs:
        sil = dome(h, w, d["dome"], d["arc"])
        solid = solid_mask(h, w, d["solids"])
        sil_all = np.maximum(sil, solid)
        rim = sil - cv2.erode(sil, kernel(41))
        jbox = rect(h, w, d["jewel"])
        interior = np.clip(sil - np.maximum(solid, rim), 0, 1)

        # unmix the glass (and the background, which comes out ~0) from the checkerboard
        region = (interior > 0.5) | (sil_all < 0.5)
        a_glass, col_glass = unmix_checker(rgb, region, D, L)
        a_glass = feather(a_glass * 0.78, 2.0)                      # residual pattern -> softer, glass a little clearer
        col_glass = cv2.GaussianBlur(col_glass, (0, 0), 2.5)
        col_glass = col_glass * 0.7 + rgb * 0.3                     # keep the tint from going muddy

        # inside the glass, opaque things (highlights, jewellery, frame) show no checker contrast
        opaque_in_glass = smoothstep(0.85, 0.98, a_glass)
        jew = jewel_fill(np.maximum(opaque_in_glass, 1 - interior), jbox)
        coverage = np.maximum(feather(solid, 1.5), np.maximum(jew, gold_key(rgb) * feather(rim, 1.0)))
        coverage = np.maximum(coverage, opaque_in_glass * interior)
        # final alpha: solids/frame/jewellery opaque, glass from the unmixing, nothing outside
        alpha = np.maximum(coverage, a_glass * interior) * feather(sil_all, 1.5)
        # any checker grey caught by the solid masks (rounded plate corners) is not object
        g = rgb.mean(axis=2)
        checker_like = (rgb.max(axis=2) - rgb.min(axis=2) < 0.07) & (g > D - 0.05) & (g < L + 0.05)
        alpha = alpha * (1 - feather(((coverage > 0.5) & checker_like).astype(np.float32), 1.0))
        colour = np.where(coverage[..., None] > 0.5, rgb, col_glass)
        x0, x1 = d["crop"]
        crop_mask = rect(h, w, (x0, 0, x1, h))
        colour_c, alpha_c = colour * crop_mask[..., None] + (1 - crop_mask[..., None]), alpha * crop_mask
        bbox = save_rgba(colour_c, alpha_c, d["name"])
        record(manifest, d, bbox, save_glints(colour_c, alpha_c, bbox, d["jewel"], d["name"]))


def main():
    for p in (SRC_BG, SRC_NECKLACE, SRC_PAIR_RE, SRC_PAIR_BP):
        if not os.path.exists(p):
            sys.exit(f"missing: {p}")
    os.makedirs(OUT, exist_ok=True)
    bg = load_rgb(SRC_BG)
    build_environment(bg)
    build_logo(bg)
    print("displays:")
    manifest = {}
    build_necklace(manifest)
    for src, specs in PAIRS:
        build_pair(src, specs, manifest)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("  manifest.json")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
