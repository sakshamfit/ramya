"""
Geetha Jewellers - SECTION 02 (Signature Gold Necklace) asset build
-------------------------------------------------------------------
    python tools/build_necklace_assets.py

Input: reference keyframe 02 from the Phase-02 spec docx (word/media/image2.jpeg).

Outputs (images/)
    gjn-bg.webp/.jpg        palace environment with the necklace lifted out, the
                            four detail-card rectangles cleared and every baked
                            text overlay removed (all rebuilt as live HTML)
    gjn-necklace.webp/.png  transparent cutout of the temple necklace - the
                            scroll-driven hero that emerges from centre/back
    gjn-card-1..4.webp/.jpg the four close-up detail images
    (the necklace webp doubles as the alpha mask for the light sweep)
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floor import dark_mask, rect_mask, synth_floor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
DEFAULT_SRC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
               r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media/image2.jpeg")

NECK_BOX = (552, 30, 972, 514)          # tight bbox around the necklace
SHADOW_BOX = (620, 490, 915, 560)       # its baked contact shadow on the podium
TEXT_OVERLAYS = [                        # deviation-matte inpaint (strokes only)
    (105, 45, 520, 495),                 # left column: eyebrow, headline, rule, body, CTA
    (1150, 45, 1475, 545),               # specifications column incl. icon tiles
    (975, 235, 1075, 420),               # scroll-to-explore cue
    (1415, 555, 1485, 825),              # "a closer look" vertical + arrow
    (180, 742, 1385, 828),               # four card captions
]
CARDS = [(205, 572, 462, 742), (500, 572, 757, 742), (795, 572, 1052, 742), (1090, 572, 1347, 742)]
SLIVER = (1344, 560, 1366, 756)          # thin rule left of "a closer look"
TILE_BOXES = [(1160, 98, 1222, 156), (1160, 168, 1222, 226), (1160, 238, 1222, 296),
              (1160, 308, 1222, 366), (1160, 378, 1222, 438)]
FLOOR_BOX = (170, 550, 1400, 864)        # the marble floor band (vase to right column)
FLOOR_LINE = 552                         # podium base / floor contact
FLOOR_EXCLUDE = [(150, 550, 196, 864)]   # the vase + its blossoms: real, never floor samples
CARD_BAND = (197, 556, 1366, 758)        # cards, their gaps + shadows and the rule sliver, as one piece
CAPTIONS = (200, 742, 1385, 828)         # card captions


def fill_vertical_blend(img, box, margin=12, sigma=9):
    """Replace a rectangle with a clean vertical blend of the rows above/below it."""
    x0, y0, x1, y1 = box
    top = img[max(0, y0 - margin):y0 - 2, x0:x1].mean(axis=0)
    bot = img[y1 + 2:y1 + margin, x0:x1].mean(axis=0)
    hgt = y1 - y0
    t = np.linspace(0, 1, hgt)[:, None, None]
    fill = top[None, :, :] * (1 - t) + bot[None, :, :] * t
    fill = cv2.GaussianBlur(fill.astype(np.float32), (0, 0), sigma)
    img[y0:y1, x0:x1] = fill
    return img


def u8(a):
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


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


def necklace_mask(rgb):
    """The necklace is crisply textured; the shallow-DOF background is soft.

    A local-detail (texture) matte separates them far more reliably than colour:
    high-frequency energy marks the metalwork, gems and chains, while the bokeh
    marble/arch stays quiet. Colour only gates out the (slightly sharp) podium
    edge. Pearl-sized enclosed holes are filled; the big C-opening stays open."""
    h, w, _ = rgb.shape
    gray = rgb.mean(axis=2).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    tex = cv2.GaussianBlur(lap, (0, 0), 2.2)
    mx, mn = rgb.max(axis=2), rgb.min(axis=2)
    sat = mx - mn
    cand = ((tex > 0.068) & (sat > 0.15)) | (tex > 0.13)
    box = np.zeros((h, w), bool)
    x0, y0, x1, y1 = NECK_BOX
    box[y0:y1, x0:x1] = True
    m = (cand & box).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel(7))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel(3))
    # keep substantial components only (drops stray bg speckles)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] > 1200:
            keep[labels == i] = 1
    def fill_small_holes(m):
        contours, hier = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        out = m.copy()
        if hier is not None:
            for i, c in enumerate(contours):
                if hier[0][i][3] != -1 and cv2.contourArea(c) < 950:
                    cv2.drawContours(out, [c], -1, 1, thickness=cv2.FILLED)
        return out

    keep = fill_small_holes(keep)
    # scrub the cream-marble halo that clings around the metalwork: bright,
    # desaturated pixels are background (pearls survive - warmer and re-filled
    # as enclosed holes right after)
    lum = rgb.mean(axis=2)
    # cream marble has r ~ g; gold has r >> g - the second clause removes the
    # warm-lit marble wedges that pass the saturation gate
    bg_like = (((sat < 0.17) & (lum > 0.78)) |
               (((rgb[..., 0] - rgb[..., 1]) < 0.09) & (lum > 0.66))).astype(np.uint8)
    keep = np.clip(keep.astype(np.int16) - bg_like, 0, 1).astype(np.uint8)
    keep = cv2.morphologyEx(keep, cv2.MORPH_OPEN, kernel(5))
    # keep only components that reach into the necklace's central window
    n, labels, stats, _ = cv2.connectedComponentsWithStats(keep, connectivity=8)
    core = np.zeros_like(keep)
    for i in range(1, n):
        xs0, ys0 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        xs1, ys1 = xs0 + stats[i, cv2.CC_STAT_WIDTH], ys0 + stats[i, cv2.CC_STAT_HEIGHT]
        if stats[i, cv2.CC_STAT_AREA] > 1500 and xs1 > 585 and xs0 < 945 and ys1 > 90:
            core[labels == i] = 1
    core = fill_small_holes(core)
    core = cv2.morphologyEx(core, cv2.MORPH_CLOSE, kernel(5))
    # hand-measured junk zones that survive every filter (arch streak at the
    # far left, floor strips flanking the hanging pearls at the bottom)
    for (ex0, ey0, ex1, ey1) in [(540, 105, 566, 520), (540, 168, 572, 520),
                                 (540, 482, 648, 522), (812, 486, 950, 522),
                                 (545, 25, 590, 118), (585, 25, 618, 58),
                                 (928, 25, 968, 172), (908, 336, 952, 480),
                                 (560, 382, 606, 460)]:
        core[ey0:ey1, ex0:ex1] = 0
    # the close() passes rounded the outline ~3px into the cream - pull it back
    core = cv2.erode(core, kernel(3))
    core = fill_small_holes(core)
    return core.astype(np.float32)


def save_pair(im: Image.Image, name: str, q=88):
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=q, method=6)
    ext = "png" if im.mode == "RGBA" else "jpg"
    if ext == "png":
        im.save(os.path.join(OUT, f"{name}.png"), "PNG", optimize=True)
    else:
        im.save(os.path.join(OUT, f"{name}.jpg"), "JPEG", quality=q, optimize=True, progressive=True)
    print(f"  {name:16s} {im.size[0]}x{im.size[1]}")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.exists(src):
        sys.exit(f"missing reference keyframe: {src}")
    os.makedirs(OUT, exist_ok=True)
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
    h, w, _ = rgb.shape
    img8 = u8(rgb)

    # ---- necklace cutout (1.5x, alpha-feathered)
    nmask = necklace_mask(rgb)
    alpha = feather(nmask, 1.2)
    ys, xs = np.where(alpha > 0.02)
    pad = 4
    by0, by1 = ys.min() - pad, ys.max() + pad + 1
    bx0, bx1 = xs.min() - pad, xs.max() + pad + 1
    crop = rgb[by0:by1, bx0:bx1]
    a = alpha[by0:by1, bx0:bx1]
    rgba = np.dstack([u8(crop), u8(a)])
    im = Image.fromarray(rgba, "RGBA")
    im = im.resize((int(im.size[0] * 1.5), int(im.size[1] * 1.5)), Image.LANCZOS)
    save_pair(im, "gjn-necklace", q=90)
    with open(os.path.join(OUT, "gjn-manifest.json"), "w", encoding="utf-8") as f:
        json.dump({  # necklace bbox as fractions of the 1536x864 scene
            "cx": round((bx0 + bx1) / 2 / w, 4), "top": round(by0 / h, 4),
            "w": round((bx1 - bx0) / w, 4), "h": round((by1 - by0) / h, 4),
        }, f, indent=2)

    # ---- environment: text strokes first (not the captions - a diffusion fill
    # next to the cards would drag their colours onto the floor; the floor pass
    # lifts them itself), then the icon-tile ghosts, then the necklace hole
    clean = cv2.inpaint(img8, deviation_mask(rgb, TEXT_OVERLAYS[:4]), 8, cv2.INPAINT_TELEA)

    clean_f = clean.astype(np.float32)
    for box in TILE_BOXES:
        clean_f = fill_vertical_blend(clean_f, box, sigma=6)
    clean = np.clip(clean_f, 0, 255).astype(np.uint8)

    hole = cv2.dilate((nmask * 255).astype(np.uint8), kernel(9))
    sx0, sy0, sx1, sy1 = SHADOW_BOX
    hole[sy0:sy1, sx0:sx1] = 255
    clean = cv2.inpaint(clean, hole, 12, cv2.INPAINT_TELEA)
    # melt the necklace fill into soft marble (no angular Telea seams)
    soft = cv2.GaussianBlur(clean.astype(np.float32), (0, 0), 19)
    wgt = cv2.GaussianBlur((hole > 0).astype(np.float32), (0, 0), 6)[..., None]
    clean = np.clip(clean.astype(np.float32) * (1 - wgt) + soft * wgt, 0, 255).astype(np.uint8)

    # the floor band: the reference hides it under the four cards (plus their
    # shadows and captions) - rebuilt as one piece of polished marble from the
    # real floor above and below it, with the podium mirrored into it; never
    # blended or blurred (the 38px gaps between the cards are too narrow to
    # keep without seams, so the whole band is one continuous surface)
    holes = np.maximum(rect_mask((h, w), [CARD_BAND]), dark_mask(rgb, [CAPTIONS]))
    clean = u8(synth_floor(clean.astype(np.float32) / 255.0, holes, FLOOR_BOX, FLOOR_LINE,
                           exclude=rect_mask((h, w), FLOOR_EXCLUDE), mode="full", mirror=0.45, feather=5))
    bg = Image.fromarray(clean)
    bg.save(os.path.join(OUT, "gjn-bg.webp"), "WEBP", quality=86, method=6)
    bg.save(os.path.join(OUT, "gjn-bg.jpg"), "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  gjn-bg           {bg.size[0]}x{bg.size[1]}")

    # ---- the four detail cards (from the ORIGINAL pixels), 1.4x for retina
    for i, (x0, y0, x1, y1) in enumerate(CARDS, 1):
        c = Image.fromarray(img8[y0:y1, x0:x1])
        c = c.resize((int(c.size[0] * 1.4), int(c.size[1] * 1.4)), Image.LANCZOS)
        p = np.asarray(c).astype(np.float32)
        blur = cv2.GaussianBlur(p, (0, 0), 1.0)
        c = Image.fromarray(np.clip(p + (p - blur) * 0.3, 0, 255).astype(np.uint8))
        save_pair(c, f"gjn-card-{i}", q=87)

    print("done ->", OUT)


if __name__ == "__main__":
    main()
