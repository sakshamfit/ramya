"""
Geetha Jewellers - SECTION 03 (Gold Rings) asset build
------------------------------------------------------
    python tools/build_rings_assets.py

Input: reference keyframe 03 from the Phase-02 spec docx (word/media/image3.jpeg).

Outputs (images/)
    gjr-bg.webp/.jpg          environment + podium, with both exploded ring stacks
                              lifted out, the thumbnail rail cleared and every baked
                              text overlay removed (all rebuilt as live HTML)
    gjr-e1..e4, gjr-h1..h4    the two rings as FOUR pieces each (webp+png, RGBA):
                              texture-matted, then sliced at the natural necks with
                              feathered cuts - exploded state is pixel-identical to
                              the reference, the compact state re-joins the slices
    gjr-t1..t5                circular collection thumbnails (glass discs)
    gjr-manifest.json         scene-fraction placement + compact offsets per piece
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floor import dark_mask, disc_mask, poly_mask, rect_mask, synth_floor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
DEFAULT_SRC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
               r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media/image3.jpeg")

SCENE_W, SCENE_H = 1536, 864

STACKS = {
    # box, horizontal cut lines (top->bottom), compact drop per piece (px, source scale)
    "e": dict(box=(505, 50, 765, 505), cuts=[243, 330, 385], drops=[100, 46, 22, 0]),
    "h": dict(box=(800, 90, 1060, 505), cuts=[270, 345, 400], drops=[95, 44, 20, 0]),
}
FEATHER_CUT = 8          # half-width of the crossfade at each slice cut

THUMBS = [  # cx, cy, half-side - generous SQUARE crops; the circle is clipped in
    # CSS with a slight zoom, so small centre offsets can never show a chord
    # (T3 stays inside its baked gold ring - the active ring is drawn in HTML)
    (287, 670, 82), (514, 674, 86), (690, 676, 78), (884, 668, 80), (1042, 670, 88),
]

TEXT_OVERLAYS = [                     # deviation-matte inpaint (strokes only)
    (108, 52, 382, 492),              # left column
    (108, 515, 295, 582),             # scroll-to-discover cue
    (1272, 78, 1475, 588),            # right column
    (405, 95, 588, 438),              # left callout labels + dotted lines
    (1002, 125, 1215, 435),           # right callout labels + dotted lines
    (1385, 710, 1505, 800),           # crafted-for-your-forever on the silk
]
CAPTION_BOX = (512, 490, 1080, 550)   # podium captions - smooth face, filled by blend
# the thumbnail rail is lifted out piece by piece and the floor beneath rebuilt
RAIL_DISCS = [(300, 678, 78), (490, 678, 78), (682, 677, 105), (870, 678, 78), (1060, 678, 78)]  # glass discs + rim + shadow
RAIL_ARROWS = [(195, 675, 29), (1170, 675, 29)]
RAIL_TEXT = (162, 738, 1198, 848)     # labels, rules, numbers, dots
FLOOR_BOX = (150, 586, 1215, 864)     # the marble floor band
FLOOR_LINE = 600                      # podium base / floor contact
FLOOR_EXCLUDE = [(1198, 560, 1250, 864), (140, 790, 200, 864)]   # right silk fold + blossoms: real, never floor samples
SILK = [(985, 864), (1090, 782), (1150, 748), (1250, 690), (1250, 864)]  # the gold silk crossing the floor's corner


def u8(a):
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def kernel(n):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (n, n))


def feather(m, sigma):
    return np.clip(cv2.GaussianBlur(m, (0, 0), sigma), 0.0, 1.0) if sigma > 0 else m


def deviation_mask(rgb, boxes, thresh=0.045, sigma=13, dilate=7):
    bg = cv2.GaussianBlur(rgb, (0, 0), sigma)
    dev = np.abs(rgb - bg).max(axis=2)
    m = np.zeros(rgb.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        sub = dev[y0:y1, x0:x1] > thresh
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], sub.astype(np.uint8) * 255)
    return cv2.dilate(m, kernel(dilate))


def fill_vertical_blend(img, box, margin=12, sigma=9):
    x0, y0, x1, y1 = box
    top = img[max(0, y0 - margin):y0 - 2, x0:x1].mean(axis=0)
    bot = img[y1 + 2:y1 + margin, x0:x1].mean(axis=0)
    t = np.linspace(0, 1, y1 - y0)[:, None, None]
    fill = top[None, :, :] * (1 - t) + bot[None, :, :] * t
    img[y0:y1, x0:x1] = cv2.GaussianBlur(fill.astype(np.float32), (0, 0), sigma)
    return img


def stack_matte(rgb, box):
    """Texture matte for a ring stack (crisp metal vs bokeh bg), leader lines removed."""
    gray = rgb.mean(axis=2).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    tex = cv2.GaussianBlur(lap, (0, 0), 2.2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    cand = (((tex > 0.06) & (sat > 0.12)) | (tex > 0.12)).astype(np.uint8)
    # kill the thin horizontal leader lines before anything can bridge to them
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
    m = np.zeros(gray.shape, np.uint8)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = cand[y0:y1, x0:x1]
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel(7))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel(3))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] > 700:
            keep[labels == i] = 1
    # fill only small sparkle holes; the band interiors must stay open
    contours, hier = cv2.findContours(keep, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is not None:
        for i, c in enumerate(contours):
            if hier[0][i][3] != -1 and cv2.contourArea(c) < 400:
                cv2.drawContours(keep, [c], -1, 1, thickness=cv2.FILLED)
    # where the leader lines touch the metal, grey stroke/letter fragments get
    # glued to the component - scrub grey (low-sat) pixels inside those strips
    lum = rgb.mean(axis=2)
    grey = (sat < 0.16) & (lum > 0.45)
    for (sx0, sy0, sx1, sy1) in [(496, 110, 590, 142), (496, 203, 590, 238), (496, 296, 590, 332), (496, 390, 590, 426),
                                 (1013, 128, 1150, 162), (1013, 220, 1150, 254), (1013, 304, 1150, 338), (1013, 396, 1150, 430)]:
        keep[sy0:sy1, sx0:sx1] &= ~grey[sy0:sy1, sx0:sx1]
    keep = cv2.morphologyEx(keep, cv2.MORPH_OPEN, kernel(3))
    return keep.astype(np.float32)


def slice_windows(y0, y1, cuts):
    """Feathered vertical windows: full inside, linear crossfade of 2*FEATHER_CUT at each cut."""
    bounds = [y0] + list(cuts) + [y1]
    wins = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        ys = np.arange(y0, y1)
        w = np.zeros(len(ys), np.float32)
        w[(ys >= a) & (ys < b)] = 1.0
        if i > 0:  # ramp in at the top cut
            r = (ys - (a - FEATHER_CUT)) / (2 * FEATHER_CUT)
            sel = (ys >= a - FEATHER_CUT) & (ys < a + FEATHER_CUT)
            w[sel] = np.clip(r[sel], 0, 1)
        if i < len(bounds) - 2:  # ramp out at the bottom cut
            b2 = bounds[i + 1]
            r = ((b2 + FEATHER_CUT) - ys) / (2 * FEATHER_CUT)
            sel = (ys >= b2 - FEATHER_CUT) & (ys < b2 + FEATHER_CUT)
            w[sel] = np.clip(r[sel], 0, 1)
        wins.append(w)
    return wins


def save_rgba(rgb, alpha, name, scale=1.5):
    ys, xs = np.where(alpha > 0.01)
    pad = 3
    y0, y1 = max(0, ys.min() - pad), min(alpha.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(alpha.shape[1], xs.max() + pad + 1)
    crop, a = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
    out = np.clip(crop, 0, 1).copy()
    out[a < 0.002] = 1.0
    im = Image.fromarray(np.dstack([u8(out), u8(a)]), "RGBA")
    if scale != 1.0:
        im = im.resize((int(im.size[0] * scale), int(im.size[1] * scale)), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=90, method=6)
    im.save(os.path.join(OUT, f"{name}.png"), "PNG", optimize=True)
    print(f"  {name:10s} {im.size[0]}x{im.size[1]}")
    return (x0, y0, x1, y1)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.exists(src):
        sys.exit(f"missing reference keyframe: {src}")
    os.makedirs(OUT, exist_ok=True)
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
    h, w, _ = rgb.shape
    img8 = u8(rgb)

    manifest = {"pieces": {}, "thumbs": []}
    hole = np.zeros((h, w), np.uint8)

    # ---- ring pieces
    print("pieces:")
    for key, spec in STACKS.items():
        box = spec["box"]
        matte = stack_matte(rgb, box)
        hole = np.maximum(hole, cv2.dilate((matte * 255).astype(np.uint8), kernel(9)))
        x0, y0, x1, y1 = box
        wins = slice_windows(y0, y1, spec["cuts"])
        for i, win in enumerate(wins):
            a = matte.copy()
            a[y0:y1, x0:x1] *= win[:, None]
            a[:y0] = 0; a[y1:] = 0
            a = feather(a, 1.0)
            if a.max() < 0.05:
                continue
            bx0, by0, bx1, by1 = save_rgba(rgb, a, f"gjr-{key}{i + 1}")
            manifest["pieces"][f"{key}{i + 1}"] = {
                "left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
                "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4),
                "drop": round(spec["drops"][i] / SCENE_H, 4),
            }

    # ---- thumbnails (square crops, circle-clipped in CSS)
    print("thumbs:")
    for i, (cx, cy, hs) in enumerate(THUMBS, 1):
        c = Image.fromarray(img8[cy - hs:cy + hs, cx - hs:cx + hs])
        c = c.resize((int(c.size[0] * 1.5), int(c.size[1] * 1.5)), Image.LANCZOS)
        c.save(os.path.join(OUT, f"gjr-t{i}.webp"), "WEBP", quality=88, method=6)
        c.save(os.path.join(OUT, f"gjr-t{i}.jpg"), "JPEG", quality=88, optimize=True)
        print(f"  gjr-t{i}     {c.size[0]}x{c.size[1]}")
        manifest["thumbs"].append(f"images/gjr-t{i}.webp")

    # ---- environment
    print("environment:")
    # text first (so the big hole fill can never smear stroke colours around),
    # with a lower-threshold second pass for the light-grey callout strokes
    clean = cv2.inpaint(img8, deviation_mask(rgb, TEXT_OVERLAYS), 8, cv2.INPAINT_TELEA)
    clean = cv2.inpaint(clean, deviation_mask(rgb, TEXT_OVERLAYS[3:5], thresh=0.028, dilate=9), 8, cv2.INPAINT_TELEA)
    # podium captions sit on a smooth marble face - a vertical blend leaves no smear
    clean = np.clip(fill_vertical_blend(clean.astype(np.float32), CAPTION_BOX, sigma=8), 0, 255).astype(np.uint8)
    clean = cv2.inpaint(clean, hole, 12, cv2.INPAINT_TELEA)
    # melt the big fills so no seams survive
    big = np.maximum(hole, 0)
    cb = CAPTION_BOX
    big[cb[1] - 6:cb[3] + 6, cb[0] - 6:cb[2] + 6] = 255
    soft = cv2.GaussianBlur(clean.astype(np.float32), (0, 0), 19)
    wgt = cv2.GaussianBlur((big > 0).astype(np.float32), (0, 0), 6)[..., None]
    clean = np.clip(clean.astype(np.float32) * (1 - wgt) + soft * wgt, 0, 255).astype(np.uint8)
    # the thumbnail rail (glass discs, arrows, labels, dots) is live HTML: lift
    # it out and rebuild the marble floor beneath from the real floor around it
    rail = np.maximum(disc_mask((h, w), RAIL_DISCS + RAIL_ARROWS), dark_mask(rgb, [RAIL_TEXT]))
    keep = np.maximum(rect_mask((h, w), FLOOR_EXCLUDE), poly_mask((h, w), SILK))
    clean = u8(synth_floor(clean.astype(np.float32) / 255.0, rail, FLOOR_BOX, FLOOR_LINE, exclude=keep))
    bg = Image.fromarray(clean)
    bg.save(os.path.join(OUT, "gjr-bg.webp"), "WEBP", quality=86, method=6)
    bg.save(os.path.join(OUT, "gjr-bg.jpg"), "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  gjr-bg     {bg.size[0]}x{bg.size[1]}")

    with open(os.path.join(OUT, "gjr-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
