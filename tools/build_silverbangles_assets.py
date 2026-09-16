"""
Geetha Jewellers - SECTION 08 (Silver Bangles) asset build
----------------------------------------------------------
    python tools/build_silverbangles_assets.py

Input: reference keyframe 08 (silver open arrangement).

Outputs (images/)
    gjb-bg8.webp/.jpg     silver open-state environment + splayed petal base
                          (bangles lifted out, all baked text/cards removed)
    gjb-sb1..sb5          the five silver bangles (hero, inner pair, outer pair)
    gjb-sc1..sc5          the five silver collection card images
    gjb-smanifest.json    scene-fraction placements
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
SPEC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
        r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media")

SCENE_W, SCENE_H = 1536, 864

# silver arrangement mirrors the gold one (same lotus, same hierarchy);
# `bottom` is a hard baseline cut so the silver-trimmed petal rims (which touch
# the bangle bases) never merge into the mattes
BANGLES = {
    # the hero's foot hides behind the heart petal - cut along its rim curve
    "sb1": dict(box=(690, 150, 860, 512), window=(715, 185, 838, 500), z=5,    # temple heritage (hero)
                cuts=[[(690, 512), (690, 486), (736, 468), (772, 468), (838, 486), (838, 512)],
                      [(730, 150), (806, 150), (806, 166), (730, 166)]]),
    "sb2": dict(box=(545, 250, 700, 520), window=(560, 283, 678, 504), z=4, cuts=[]),   # heritage inspired
    "sb3": dict(box=(850, 243, 1012, 520), window=(872, 276, 1000, 504), z=4, cuts=[]),  # timeless beauty
    "sb4": dict(box=(375, 318, 566, 540), window=(398, 347, 550, 514), z=3, cuts=[]),   # everyday elegance
    "sb5": dict(box=(952, 308, 1168, 540), window=(972, 336, 1150, 514), z=3, cuts=[]),  # modern sophistication
}
# painted node/stem positions in keyframe 08 (cleaned even over the bangle tops)
KF8_NODES = [(433, 344), (587, 247), (767, 156), (958, 247), (1113, 344)]
# the annotation band (arc line, nodes, labels, top mark + cue line) is cleaned
# BEFORE matting so neither the cutouts nor the background inherit fragments
ANN_BAND = (368, 0, 1180, 360)
KF8_TEXT = [
    (84, 112, 450, 282),              # eyebrow + title
    (84, 282, 352, 442),              # ornament + description
    (95, 455, 348, 514),              # CTA
    (1355, 135, 1478, 475),           # right captions (tile squares filled separately)
    (1283, 486, 1438, 630),           # divider + quote
    (548, 592, 985, 655),             # five expressions line
    (120, 530, 230, 565),             # decorative tick left of the podium
    (1240, 616, 1400, 664),           # decorative tick right of the podium
    (160, 718, 214, 774),             # left arrow
    (1330, 715, 1385, 770),           # right arrow
]
CARDS8 = [(240, 688, 430, 764), (455, 688, 645, 764), (672, 688, 860, 764),
          (885, 688, 1075, 764), (1100, 688, 1290, 764)]
CARD_BAND = (225, 678, 1302, 832)
TILE8_BOXES = [(1288, 138, 1348, 198), (1288, 206, 1348, 266), (1288, 274, 1348, 334),
               (1288, 342, 1348, 402), (1288, 410, 1348, 470)]


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


def silver_matte(rgb, box, window=None, min_area=2500, tex_lo=0.05, cuts=()):
    """Silver on bright marble: pure texture matte; the petal rims that touch
    the bangle feet are removed structurally (baseline + corner cuts)."""
    gray = rgb.mean(axis=2).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    tex = cv2.GaussianBlur(lap, (0, 0), 2.2)
    cand = (tex > tex_lo).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
    m = np.zeros(gray.shape, np.uint8)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = cand[y0:y1, x0:x1]
    if window:
        m[window[3] + 6:, :] = 0          # hard baseline: nothing below the bangle's foot
    for poly in cuts:
        cv2.fillPoly(m, [np.array(poly, np.int32)], 0)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel(9))
    for poly in cuts:                     # re-cut: close() may bridge the seam
        cv2.fillPoly(m, [np.array(poly, np.int32)], 0)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel(3))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        bx0, by0 = stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_TOP]
        bx1, by1 = bx0 + stats[i, cv2.CC_STAT_WIDTH], by0 + stats[i, cv2.CC_STAT_HEIGHT]
        ok = stats[i, cv2.CC_STAT_AREA] > min_area
        if ok and window:
            wx0, wy0, wx1, wy1 = window
            ok = bx1 > wx0 and bx0 < wx1 and by1 > wy0 and by0 < wy1
        if ok:
            keep[labels == i] = 1
    # keep the big openings transparent, fill only small texture holes
    contours, hier = cv2.findContours(keep, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is not None:
        for i, c in enumerate(contours):
            if hier[0][i][3] != -1 and cv2.contourArea(c) < 450:
                cv2.drawContours(keep, [c], -1, 1, thickness=cv2.FILLED)
    keep = cv2.erode(keep, kernel(2))
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
    print(f"  {name:8s} {im.size[0]}x{im.size[1]}")
    return (x0, y0, x1, y1)


def save_bg(clean, holes, name, extra_melt=()):
    big = holes.copy()
    for (x0, y0, x1, y1) in extra_melt:
        big[y0 - 6:y1 + 6, x0 - 6:x1 + 6] = 255
    soft = cv2.GaussianBlur(clean.astype(np.float32), (0, 0), 19)
    wgt = cv2.GaussianBlur((big > 0).astype(np.float32), (0, 0), 6)[..., None]
    clean = np.clip(clean.astype(np.float32) * (1 - wgt) + soft * wgt, 0, 255).astype(np.uint8)
    im = Image.fromarray(clean)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=86, method=6)
    im.save(os.path.join(OUT, f"{name}.jpg"), "JPEG", quality=86, optimize=True, progressive=True)
    print(f"  {name:8s} {im.size[0]}x{im.size[1]}")


def main():
    manifest = {"bangles": {}}

    src8 = os.path.join(SPEC, "image8.jpeg")
    img8 = np.asarray(Image.open(src8).convert("RGB"))
    rgb8 = img8.astype(np.float32) / 255.0
    h, w, _ = rgb8.shape

    # clean the annotation band first: mattes and cutout pixels both come from
    # the cleaned plate, so no node/arc/label fragments survive anywhere.
    # The bangles live inside the band - protect them from their window-top
    # down (labels/lines above still clean), but always clean the node dots.
    def band_mask(th, di):
        m = deviation_mask(rgb8, [ANN_BAND], thresh=th, dilate=di)
        for spec in BANGLES.values():
            x0, _, x1, y1 = spec["box"]
            m[spec["window"][1] - 2:y1, x0:x1] = 0
        for (nx, ny) in KF8_NODES:
            m[ny - 13:ny + 13, nx - 13:nx + 13] = 255
        return m
    work = cv2.inpaint(img8, band_mask(0.045, 7), 8, cv2.INPAINT_TELEA)
    work = cv2.inpaint(work, band_mask(0.024, 11), 8, cv2.INPAINT_TELEA)
    wrgb = work.astype(np.float32) / 255.0

    print("silver open state:")
    hole8 = np.zeros((h, w), np.uint8)
    for key, spec in BANGLES.items():
        matte = silver_matte(wrgb, spec["box"], window=spec["window"], min_area=2500, cuts=spec["cuts"])
        hole8 = np.maximum(hole8, cv2.dilate((matte * 255).astype(np.uint8), kernel(9)))
        a = feather(matte, 1.0)
        bx0, by0, bx1, by1 = save_rgba(wrgb, a, f"gjb-{key}")
        manifest["bangles"][key] = {
            "left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
            "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4),
            "z": spec["z"],
        }

    print("cards:")
    for i, (x0, y0, x1, y1) in enumerate(CARDS8, 1):
        c = Image.fromarray(img8[y0:y1, x0:x1])
        c = c.resize((int(c.size[0] * 1.4), int(c.size[1] * 1.4)), Image.LANCZOS)
        c.save(os.path.join(OUT, f"gjb-sc{i}.webp"), "WEBP", quality=88, method=6)
        c.save(os.path.join(OUT, f"gjb-sc{i}.jpg"), "JPEG", quality=88, optimize=True)
        print(f"  gjb-sc{i}  {c.size[0]}x{c.size[1]}")

    print("silver environment:")
    cf = work.astype(np.float32)
    cf = fill_vertical_blend(cf, CARD_BAND, sigma=11)
    bx0, by0, bx1, by1 = CARD_BAND
    cf[by0:by1, bx0:bx1] = cv2.GaussianBlur(cf[by0:by1, bx0:bx1], (0, 0), sigmaX=27, sigmaY=7)
    for tb in TILE8_BOXES:
        cf = fill_vertical_blend(cf, tb, sigma=6)
    clean8 = np.clip(cf, 0, 255).astype(np.uint8)
    clean8 = cv2.inpaint(clean8, deviation_mask(rgb8, KF8_TEXT), 8, cv2.INPAINT_TELEA)
    clean8 = cv2.inpaint(clean8, hole8, 12, cv2.INPAINT_TELEA)
    save_bg(clean8, hole8, "gjb-bg8", extra_melt=[CARD_BAND] + TILE8_BOXES)

    with open(os.path.join(OUT, "gjb-smanifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
