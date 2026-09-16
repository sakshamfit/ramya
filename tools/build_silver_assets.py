"""
Geetha Jewellers - SECTION 04 (Silver Rings) asset build
--------------------------------------------------------
    python tools/build_silver_assets.py

Input: reference keyframe 04 from the Phase-02 spec docx (word/media/image4.jpeg).

Outputs (images/)
    gjs-bg.webp/.jpg     silver environment + slim podium, with both rings lifted
                         out, the thumbnail rail cleared and every baked text
                         overlay removed (all rebuilt as live HTML)
    gjs-r1, gjs-r2       The Radiance / The Blossom as whole transparent rings
                         (texture-matted; silver is desaturated, so no colour gate)
    gjs-t1..t5           square thumbnail crops (circle-clipped in CSS)
    gjs-manifest.json    scene-fraction placement for both rings

The silver state shares Section 03's compositional framework: same 16:9 scene
layer, same podium logic - only the jewellery/product state and copy change.
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floor import dark_mask, disc_mask, rect_mask, synth_floor  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
DEFAULT_SRC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
               r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media/image4.jpeg")

SCENE_W, SCENE_H = 1536, 864

RINGS = {
    # matte box + a central window the main component must reach into
    "r1": dict(box=(512, 100, 752, 444), window=(560, 150, 710, 430)),   # The Radiance
    "r2": dict(box=(830, 150, 1100, 454), window=(880, 200, 1050, 440)),  # The Blossom
}

# strips fully OUTSIDE the metal where the leader lines approach - hard-zeroed
LINE_STRIPS = [
    (492, 136, 521, 172), (492, 226, 521, 260), (492, 312, 521, 346), (492, 396, 521, 430),
    (1097, 160, 1175, 200), (1097, 235, 1175, 275), (1097, 358, 1175, 400),
]

CONTACT_SHADOWS = [(515, 436, 758, 474), (828, 444, 1104, 480)]   # baked reflections under the bands

THUMBS = [  # cx, cy, half-side - generous square crops, circle-clipped in CSS
    (363, 662, 84), (546, 662, 82), (739, 660, 78), (926, 662, 80), (1098, 662, 80),
]

TEXT_OVERLAYS = [                     # deviation-matte inpaint (strokes only)
    (92, 60, 392, 500),               # left column
    (92, 528, 305, 598),              # scroll-to-discover cue
    (1278, 68, 1475, 775),            # right aside incl. crafted-for-your-forever
    (400, 128, 588, 442),             # left callout labels + dotted lines (through to the metal)
    (998, 150, 1245, 410),            # right callout labels + dotted lines (through to the metal)
]
CAPTION_BOX = (455, 480, 1125, 544)   # podium captions - smooth face, filled by blend
# the thumbnail rail is lifted out piece by piece and the floor beneath rebuilt
RAIL_DISCS = [(358, 669, 79), (548, 669, 79), (740, 672, 106), (928, 669, 79), (1100, 669, 79)]  # glass discs + rim + shadow
RAIL_ARROWS = [(252, 668, 29), (1213, 668, 29)]
RAIL_TEXT = (222, 722, 1262, 838)     # labels, rules, numbers, dots
FLOOR_BOX = (205, 574, 1275, 864)     # the marble floor band
FLOOR_LINE = 578                      # podium base / floor contact
FLOOR_EXCLUDE = [(195, 745, 300, 864), (1160, 735, 1300, 864)]   # bokeh blossoms: real, never floor samples


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


def ring_matte(rgb, box, window):
    """Texture matte for a silver ring: the metal is desaturated, so there is no
    colour gate - crisp pave/metal detail vs the smooth bokeh colonnade is the
    whole separation. Thin horizontal leader lines and the (in-focus) podium
    edge are killed by a vertical-kernel opening before anything can bridge."""
    gray = rgb.mean(axis=2).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    tex = cv2.GaussianBlur(lap, (0, 0), 2.2)
    cand = (tex > 0.05).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
    m = np.zeros(gray.shape, np.uint8)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = cand[y0:y1, x0:x1]
    for (sx0, sy0, sx1, sy1) in LINE_STRIPS:
        m[sy0:sy1, sx0:sx1] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel(7))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel(3))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    wx0, wy0, wx1, wy1 = window
    for i in range(1, n):
        bx0, by0 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        bx1, by1 = bx0 + stats[i, cv2.CC_STAT_WIDTH], by0 + stats[i, cv2.CC_STAT_HEIGHT]
        if stats[i, cv2.CC_STAT_AREA] > 1500 and bx1 > wx0 and bx0 < wx1 and by1 > wy0 and by0 < wy1:
            keep[labels == i] = 1
    # fill only small sparkle holes; the band interior must stay open
    contours, hier = cv2.findContours(keep, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is not None:
        for i, c in enumerate(contours):
            if hier[0][i][3] != -1 and cv2.contourArea(c) < 420:
                cv2.drawContours(keep, [c], -1, 1, thickness=cv2.FILLED)
    # glued leader-line stubs + the in-focus podium edge are THIN HORIZONTAL
    # appendages; close(7) fattened them to ~10-16px, so open with a 21px
    # vertical kernel on a PADDED window (so metal continuing past the box
    # is not clipped by the box edge) and write back only the inner rows
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 21))
    PAD = 24
    H, W = keep.shape
    for (ax0, ay0, ax1, ay1) in [(490, 134, 575, 176), (490, 222, 575, 264), (490, 308, 575, 350), (490, 392, 575, 434),
                                 (1008, 158, 1180, 200), (1040, 234, 1180, 278), (1040, 356, 1180, 402),
                                 (505, 424, 768, 448), (824, 438, 1108, 460)]:
        py0, py1 = max(0, ay0 - PAD), min(H, ay1 + PAD)
        opened = cv2.morphologyEx(keep[py0:py1, ax0:ax1], cv2.MORPH_OPEN, vk)
        keep[ay0:ay1, ax0:ax1] = opened[ay0 - py0:ay1 - py0]
    # pull the outline out of the warm bokeh halo
    keep = cv2.erode(keep, kernel(3))
    return keep.astype(np.float32)


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

    manifest = {"rings": {}}
    hole = np.zeros((h, w), np.uint8)

    print("rings:")
    for key, spec in RINGS.items():
        matte = ring_matte(rgb, spec["box"], spec["window"])
        hole = np.maximum(hole, cv2.dilate((matte * 255).astype(np.uint8), kernel(9)))
        a = feather(matte, 1.0)
        bx0, by0, bx1, by1 = save_rgba(rgb, a, f"gjs-{key}")
        manifest["rings"][key] = {
            "left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
            "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4),
        }
    for (x0, y0, x1, y1) in CONTACT_SHADOWS:
        hole[y0:y1, x0:x1] = 255

    print("thumbs:")
    for i, (cx, cy, hs) in enumerate(THUMBS, 1):
        c = Image.fromarray(img8[cy - hs:cy + hs, cx - hs:cx + hs])
        c = c.resize((int(c.size[0] * 1.5), int(c.size[1] * 1.5)), Image.LANCZOS)
        c.save(os.path.join(OUT, f"gjs-t{i}.webp"), "WEBP", quality=88, method=6)
        c.save(os.path.join(OUT, f"gjs-t{i}.jpg"), "JPEG", quality=88, optimize=True)
        print(f"  gjs-t{i}     {c.size[0]}x{c.size[1]}")

    print("environment:")
    # text first (so the hole fill can never smear stroke colours), low-threshold
    # second pass for the light-grey callout strokes
    clean = cv2.inpaint(img8, deviation_mask(rgb, TEXT_OVERLAYS), 8, cv2.INPAINT_TELEA)
    clean = cv2.inpaint(clean, deviation_mask(rgb, TEXT_OVERLAYS[3:5], thresh=0.028, dilate=9), 8, cv2.INPAINT_TELEA)
    clean = np.clip(fill_vertical_blend(clean.astype(np.float32), CAPTION_BOX, sigma=8), 0, 255).astype(np.uint8)
    clean = cv2.inpaint(clean, hole, 12, cv2.INPAINT_TELEA)
    # melt the big fills so no seams survive
    big = hole.copy()
    cb = CAPTION_BOX
    big[cb[1] - 6:cb[3] + 6, cb[0] - 6:cb[2] + 6] = 255
    for (ox0, oy0, ox1, oy1) in TEXT_OVERLAYS[3:5]:      # callout zones: diffuse the box edges
        big[oy0 - 6:oy1 + 6, ox0 - 6:ox1 + 6] = 255
    soft = cv2.GaussianBlur(clean.astype(np.float32), (0, 0), 19)
    wgt = cv2.GaussianBlur((big > 0).astype(np.float32), (0, 0), 6)[..., None]
    clean = np.clip(clean.astype(np.float32) * (1 - wgt) + soft * wgt, 0, 255).astype(np.uint8)
    # the thumbnail rail (glass discs, arrows, labels, dots) is live HTML: lift
    # it out and rebuild the marble floor beneath from the real floor around it
    rail = np.maximum(disc_mask((h, w), RAIL_DISCS + RAIL_ARROWS), dark_mask(rgb, [RAIL_TEXT]))
    clean = u8(synth_floor(clean.astype(np.float32) / 255.0, rail, FLOOR_BOX, FLOOR_LINE,
                           exclude=rect_mask((h, w), FLOOR_EXCLUDE)))
    bg = Image.fromarray(clean)
    bg.save(os.path.join(OUT, "gjs-bg.webp"), "WEBP", quality=86, method=6)
    bg.save(os.path.join(OUT, "gjs-bg.jpg"), "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  gjs-bg     {bg.size[0]}x{bg.size[1]}")

    with open(os.path.join(OUT, "gjs-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
