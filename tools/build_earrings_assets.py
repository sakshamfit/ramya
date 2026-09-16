"""
Geetha Jewellers - SECTION 05 (Earrings) asset build
----------------------------------------------------
    python tools/build_earrings_assets.py

Input: reference keyframe 05 from the Phase-02 spec docx (word/media/image5.jpeg).

Outputs (images/)
    gje-bg.webp/.jpg     environment + podium, with all five hanging panels (and
                         their wires) lifted out and every baked text overlay
                         removed (all rebuilt as live HTML)
    gje-p1..p5           the five suspended glass display panels, each WITH its
                         hanging wire, as silhouette-filled RGBA cutouts (the
                         frosted glass interior stays baked - the sway is subtle,
                         so the panel reads as real glass in motion)
    gje-manifest.json    scene-fraction placement per panel

Panel silhouettes come from the crisp gold rims + contents via the texture
matte, with ALL enclosed holes filled (the glass interior is ringed by the
rim). Overlaps between neighbouring panels are resolved by the crop boxes so
the front panel keeps the shared edge (matching the visual stacking).
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
DEFAULT_SRC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
               r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media/image5.jpeg")

SCENE_W, SCENE_H = 1536, 864

# crop boxes reach y=0 so each panel keeps its hanging wire; the shared edges
# go to the panel that is visually IN FRONT (p3 > p2/p4 > p1/p5)
PANELS = {
    "p1": dict(box=(335, 0, 496, 545), window=(365, 300, 480, 500)),
    "p2": dict(box=(486, 0, 657, 540), window=(505, 250, 640, 480)),
    "p3": dict(box=(655, 0, 906, 558), window=(680, 120, 880, 520)),
    "p4": dict(box=(903, 0, 1067, 540), window=(915, 250, 1050, 480)),
    "p5": dict(box=(1063, 0, 1200, 548), window=(1070, 300, 1190, 500)),
}

# labels baked inside the glass of every panel - all rebuilt as live HTML
LABEL_BOXES = [(695, 445, 875, 510),    # traditional jhumkas (hero)
               (366, 496, 478, 534),    # diamond drops
               (514, 488, 642, 532),    # pearl elegance
               (923, 486, 1044, 530),   # temple artistry
               (1070, 498, 1188, 540)]  # modern classics

TEXT_OVERLAYS = [                     # deviation-matte inpaint (strokes only)
    (88, 52, 345, 442),               # left column: eyebrow, headline, orn, body, CTA
    (26, 445, 220, 655),              # left section index 01..05
    (26, 685, 220, 790),              # scroll-to-explore cue
    (1240, 52, 1505, 580),            # right featured column incl. spec tiles
    (1395, 620, 1505, 665),           # drag-to-rotate text + arrows
    (570, 770, 970, 845),             # italic quote + ornament on the silk
    (1315, 782, 1505, 835),           # geetha jewellers / since 1998 mark
    (322, 152, 378, 198),             # stray glyph fragment left of panel 1
]
BADGE_BOX = (1296, 606, 1396, 692)    # the 360-degree gold badge (solid disc)
PODIUM_TEXT_BOX = (555, 612, 1005, 684)   # five styles / endless expressions + ornament

TILE_BOXES = [(1248, 328, 1302, 382), (1248, 392, 1302, 446),
              (1248, 448, 1302, 508), (1248, 512, 1302, 568)]   # icon tile ghosts


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


def inpaint_box(img8, box, radius=8, thresh=0.045):
    rgb = img8.astype(np.float32) / 255.0
    return cv2.inpaint(img8, deviation_mask(rgb, [box], thresh=thresh), radius, cv2.INPAINT_TELEA)


def panel_matte(rgb, box, window):
    """Filled silhouette of one hanging panel + its wire."""
    gray = rgb.mean(axis=2).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    tex = cv2.GaussianBlur(lap, (0, 0), 2.2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    cand = (((tex > 0.05) & (sat > 0.08)) | (tex > 0.11)).astype(np.uint8)
    m = np.zeros(gray.shape, np.uint8)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = cand[y0:y1, x0:x1]
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel(9))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel(3))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    wx0, wy0, wx1, wy1 = window
    for i in range(1, n):
        bx0, by0 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        bx1, by1 = bx0 + stats[i, cv2.CC_STAT_WIDTH], by0 + stats[i, cv2.CC_STAT_HEIGHT]
        big = stats[i, cv2.CC_STAT_AREA] > 2500 and bx1 > wx0 and bx0 < wx1 and by1 > wy0 and by0 < wy1
        wire = stats[i, cv2.CC_STAT_AREA] > 150 and by0 < 60 and stats[i, cv2.CC_STAT_HEIGHT] > 50
        if big or wire:
            keep[labels == i] = 1
    # the glass interior is enclosed by the rim: fill EVERY hole
    contours, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(keep)
    cv2.drawContours(filled, contours, -1, 1, thickness=cv2.FILLED)
    filled = cv2.erode(filled, kernel(2))
    return filled.astype(np.float32)


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
    print(f"  {name:8s} {im.size[0]}x{im.size[1]}")
    return (x0, y0, x1, y1)


def fill_vertical_blend(img, box, margin=12, sigma=9):
    x0, y0, x1, y1 = box
    top = img[max(0, y0 - margin):y0 - 2, x0:x1].mean(axis=0)
    bot = img[y1 + 2:y1 + margin, x0:x1].mean(axis=0)
    t = np.linspace(0, 1, y1 - y0)[:, None, None]
    fill = top[None, :, :] * (1 - t) + bot[None, :, :] * t
    img[y0:y1, x0:x1] = cv2.GaussianBlur(fill.astype(np.float32), (0, 0), sigma)
    return img


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.exists(src):
        sys.exit(f"missing reference keyframe: {src}")
    os.makedirs(OUT, exist_ok=True)
    img8 = np.asarray(Image.open(src).convert("RGB"))
    # every panel's baked label comes out FIRST, so the cutouts and the
    # environment are label-free (rebuilt as live HTML on/under the glass)
    for lb in LABEL_BOXES:
        img8 = inpaint_box(img8, lb, thresh=0.04)
    rgb = img8.astype(np.float32) / 255.0
    h, w, _ = rgb.shape

    manifest = {"panels": {}}
    hole = np.zeros((h, w), np.uint8)

    print("panels:")
    for key, spec in PANELS.items():
        matte = panel_matte(rgb, spec["box"], spec["window"])
        hole = np.maximum(hole, cv2.dilate((matte * 255).astype(np.uint8), kernel(9)))
        a = feather(matte, 1.1)
        bx0, by0, bx1, by1 = save_rgba(rgb, a, f"gje-{key}")
        manifest["panels"][key] = {
            "left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
            "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4),
        }

    print("environment:")
    clean = img8.copy()
    clean = cv2.inpaint(clean, deviation_mask(rgb, TEXT_OVERLAYS), 8, cv2.INPAINT_TELEA)
    clean = cv2.inpaint(clean, deviation_mask(rgb, TEXT_OVERLAYS[3:5], thresh=0.028, dilate=9), 8, cv2.INPAINT_TELEA)
    # solid fills: the 360 badge disc + the icon-tile ghosts
    cf = clean.astype(np.float32)
    cf = fill_vertical_blend(cf, BADGE_BOX, sigma=8)
    for tb in TILE_BOXES:
        cf = fill_vertical_blend(cf, tb, sigma=6)
    clean = np.clip(cf, 0, 255).astype(np.uint8)
    # podium face text sits among filigree - stroke-level inpaint, tight box
    clean = inpaint_box(clean, PODIUM_TEXT_BOX, radius=6, thresh=0.05)
    clean = cv2.inpaint(clean, hole, 12, cv2.INPAINT_TELEA)
    # melt the panel holes + badge + tiles so no seams survive
    big = hole.copy()
    bb = BADGE_BOX
    big[bb[1] - 6:bb[3] + 6, bb[0] - 6:bb[2] + 6] = 255
    for tb in TILE_BOXES:
        big[tb[1] - 5:tb[3] + 5, tb[0] - 5:tb[2] + 5] = 255
    soft = cv2.GaussianBlur(clean.astype(np.float32), (0, 0), 19)
    wgt = cv2.GaussianBlur((big > 0).astype(np.float32), (0, 0), 6)[..., None]
    clean = np.clip(clean.astype(np.float32) * (1 - wgt) + soft * wgt, 0, 255).astype(np.uint8)
    bg = Image.fromarray(clean)
    bg.save(os.path.join(OUT, "gje-bg.webp"), "WEBP", quality=86, method=6)
    bg.save(os.path.join(OUT, "gje-bg.jpg"), "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  gje-bg   {bg.size[0]}x{bg.size[1]}")

    with open(os.path.join(OUT, "gje-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
