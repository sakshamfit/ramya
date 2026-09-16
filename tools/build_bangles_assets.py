"""
Geetha Jewellers - SECTIONS 06/07 (Gold Bangles) asset build
------------------------------------------------------------
    python tools/build_bangles_assets.py

Inputs: reference keyframes 06 (closed lotus) + 07 (open arrangement).

Outputs (images/)
    gjb-bg6.webp/.jpg    closed-state environment + podium, bud lifted out,
                         all baked text removed
    gjb-bud.webp/.png    the closed marble lotus bud (whole; the section slices
                         it into four feathered petal groups in CSS for the
                         scroll-driven opening)
    gjb-bg7.webp/.jpg    open-state environment + podium + SPLAYED PETAL BASE
                         (bangles lifted out, all text/cards/arc removed)
    gjb-b1..b5           the five bangles (hero, inner pair, outer pair)
    gjb-c1..c5           the five collection card images
    gjb-manifest.json    scene-fraction placements
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
SPEC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
        r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media")

SCENE_W, SCENE_H = 1536, 864

# ---- keyframe 06 (closed)
BUD_BOX = (580, 238, 950, 614)
KF6_TEXT = [
    (92, 92, 452, 498),               # left column
    (698, 0, 852, 248),               # scroll-to-unveil cue stack
    (1238, 115, 1472, 640),           # right column incl. its divider rule
    (618, 636, 932, 696),             # a story waiting to unfold
    (690, 798, 850, 828),             # dots
]

# ---- keyframe 07 (open)
BANGLES = {
    "b1": dict(box=(695, 133, 860, 507), window=(720, 170, 840, 480), z=5),   # temple heritage (hero)
    "b2": dict(box=(523, 253, 697, 527), window=(545, 285, 675, 500), z=4),   # diamond radiance
    "b3": dict(box=(858, 243, 1017, 527), window=(880, 275, 1000, 500), z=4), # royal tradition
    "b4": dict(box=(378, 323, 523, 547), window=(400, 350, 505, 520), z=3),   # everyday elegance
    "b5": dict(box=(1017, 313, 1142, 552), window=(1035, 340, 1125, 525), z=3),  # modern minimal
}
KF7_TEXT = [
    (82, 88, 442, 498),               # left column (same copy as 06)
    (368, 62, 1175, 345),             # arc labels + nodes band
    (85, 518, 218, 562),              # small decorative strip left of the podium
    (1278, 100, 1478, 625),           # right tiles + quote
    (548, 592, 985, 652),             # five expressions line
    (62, 550, 115, 770),              # vertical scroll-to-explore
    (160, 720, 212, 772),             # left arrow
    (1335, 720, 1388, 772),           # right arrow
]
CARDS7 = [(240, 688, 430, 766), (455, 688, 645, 766), (672, 688, 860, 766),
          (885, 688, 1075, 766), (1100, 688, 1290, 766)]
CARD_BAND = (225, 678, 1302, 832)
TILE7_BOXES = [(1288, 122, 1348, 180), (1288, 186, 1348, 244), (1288, 250, 1348, 308),
               (1288, 314, 1348, 372), (1288, 378, 1348, 436)]


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


def silhouette_matte(rgb, box, window=None, min_area=2500, fill_all=True):
    """Crisp-edged object over bokeh: texture matte, closed + hole-filled."""
    gray = rgb.mean(axis=2).astype(np.float32)
    lap = np.abs(cv2.Laplacian(gray, cv2.CV_32F, ksize=3))
    tex = cv2.GaussianBlur(lap, (0, 0), 2.2)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    cand = (((tex > 0.05) & (sat > 0.08)) | (tex > 0.11)).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
    m = np.zeros(gray.shape, np.uint8)
    x0, y0, x1, y1 = box
    m[y0:y1, x0:x1] = cand[y0:y1, x0:x1]
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel(9))
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
    if fill_all:
        contours, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(keep)
        cv2.drawContours(filled, contours, -1, 1, thickness=cv2.FILLED)
        keep = filled
    else:
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
    manifest = {"bud": {}, "bangles": {}}

    # ================= keyframe 06 (closed)
    src6 = os.path.join(SPEC, "image6.jpeg")
    img6 = np.asarray(Image.open(src6).convert("RGB"))
    rgb6 = img6.astype(np.float32) / 255.0
    h, w, _ = rgb6.shape
    print("closed state:")
    bud = silhouette_matte(rgb6, BUD_BOX, min_area=6000, fill_all=True)
    # soften the seam where the bud meets the podium
    bud[606:] = 0
    a = feather(bud, 1.1)
    bx0, by0, bx1, by1 = save_rgba(rgb6, a, "gjb-bud")
    manifest["bud"] = {"left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
                       "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4)}
    hole6 = cv2.dilate((bud * 255).astype(np.uint8), kernel(9))
    clean6 = cv2.inpaint(img6, deviation_mask(rgb6, KF6_TEXT), 8, cv2.INPAINT_TELEA)
    clean6 = cv2.inpaint(clean6, hole6, 12, cv2.INPAINT_TELEA)
    save_bg(clean6, hole6, "gjb-bg6")

    # ================= keyframe 07 (open)
    src7 = os.path.join(SPEC, "image7.jpeg")
    img7 = np.asarray(Image.open(src7).convert("RGB"))
    rgb7 = img7.astype(np.float32) / 255.0
    print("open state:")
    hole7 = np.zeros((h, w), np.uint8)
    for key, spec in BANGLES.items():
        matte = silhouette_matte(rgb7, spec["box"], window=spec["window"], min_area=2500, fill_all=False)
        hole7 = np.maximum(hole7, cv2.dilate((matte * 255).astype(np.uint8), kernel(9)))
        a = feather(matte, 1.0)
        bx0, by0, bx1, by1 = save_rgba(rgb7, a, f"gjb-{key}")
        manifest["bangles"][key] = {
            "left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
            "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4),
            "z": spec["z"],
        }

    print("cards:")
    for i, (x0, y0, x1, y1) in enumerate(CARDS7, 1):
        c = Image.fromarray(img7[y0:y1, x0:x1])
        c = c.resize((int(c.size[0] * 1.4), int(c.size[1] * 1.4)), Image.LANCZOS)
        c.save(os.path.join(OUT, f"gjb-c{i}.webp"), "WEBP", quality=88, method=6)
        c.save(os.path.join(OUT, f"gjb-c{i}.jpg"), "JPEG", quality=88, optimize=True)
        print(f"  gjb-c{i}   {c.size[0]}x{c.size[1]}")

    print("open environment:")
    cf = img7.astype(np.float32)
    cf = fill_vertical_blend(cf, CARD_BAND, sigma=11)
    bx0, by0, bx1, by1 = CARD_BAND
    cf[by0:by1, bx0:bx1] = cv2.GaussianBlur(cf[by0:by1, bx0:bx1], (0, 0), sigmaX=27, sigmaY=7)
    for tb in TILE7_BOXES:
        cf = fill_vertical_blend(cf, tb, sigma=6)
    clean7 = np.clip(cf, 0, 255).astype(np.uint8)
    clean7 = cv2.inpaint(clean7, deviation_mask(rgb7, KF7_TEXT), 8, cv2.INPAINT_TELEA)
    clean7 = cv2.inpaint(clean7, deviation_mask(rgb7, [KF7_TEXT[1]], thresh=0.024, dilate=11), 8, cv2.INPAINT_TELEA)
    clean7 = cv2.inpaint(clean7, hole7, 12, cv2.INPAINT_TELEA)
    save_bg(clean7, hole7, "gjb-bg7", extra_melt=[CARD_BAND] + TILE7_BOXES)

    with open(os.path.join(OUT, "gjb-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
