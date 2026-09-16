"""
Geetha Jewellers - PHASE 01 (Cinematic Intro) assets
----------------------------------------------------
    python tools/build_intro_assets.py

Inputs: Phase-01 keyframes A/B/C (image1/2/3 of the intro document).

Outputs (images/)
    gji-gold.webp/.jpg   keyframe A macro gold surface, untouched (revealed
                         by light; the baked composition IS keyframe A)
    gji-hall.webp/.jpg   keyframe C colonnade with the centre lockup lifted
    gji-emblem.webp/.png the polished GJS coin from keyframe B (circular
                         alpha with a soft glow falloff)
"""
from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
SPEC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
        r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec1/unpacked/word/media")

A_TEXT = [(390, 556, 1125, 643), (426, 643, 1094, 702)]
C_TEXT = [(694, 286, 842, 432), (604, 430, 916, 476), (614, 474, 906, 504)]
B_COIN = dict(cx=772, cy=251, r=134)


def kernel(n):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (n, n))


def deviation_mask(rgb, boxes, thresh=0.045, sigma=13, dilate=7):
    bg = cv2.GaussianBlur(rgb, (0, 0), sigma)
    dev = np.abs(rgb - bg).max(axis=2)
    m = np.zeros(rgb.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        sub = dev[y0:y1, x0:x1] > thresh
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], sub.astype(np.uint8) * 255)
    return cv2.dilate(m, kernel(dilate))


def melt(img, boxes, sigma_soft=13, sigma_w=6):
    hole = np.zeros(img.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        hole[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = 255
    soft = cv2.GaussianBlur(img.astype(np.float32), (0, 0), sigma_soft)
    w = cv2.GaussianBlur((hole > 0).astype(np.float32), (0, 0), sigma_w)[..., None]
    return np.clip(img.astype(np.float32) * (1 - w) + soft * w, 0, 255).astype(np.uint8)


def save_plate(arr, name, q=86):
    im = Image.fromarray(arr)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=q, method=6)
    im.save(os.path.join(OUT, f"{name}.jpg"), "JPEG", quality=q, optimize=True, progressive=True)
    print(f"  {name:10s} {im.size[0]}x{im.size[1]}")


def main():
    a = np.asarray(Image.open(os.path.join(SPEC, "image1.jpeg")).convert("RGB"))
    b = np.asarray(Image.open(os.path.join(SPEC, "image2.jpeg")).convert("RGB"))
    c = np.asarray(Image.open(os.path.join(SPEC, "image3.jpeg")).convert("RGB"))

    print("plates:")
    # keyframe A ships UNTOUCHED - its baked emblem/wordmark IS the reference
    # composition; the intro reveals it with light and hands off to the live
    # lockup under the keyframe-B bloom pulse
    save_plate(a, "gji-gold")

    rc = c.astype(np.float32) / 255.0
    cc = cv2.inpaint(c, deviation_mask(rc, C_TEXT, thresh=0.03, dilate=9), 8, cv2.INPAINT_TELEA)
    cc = cv2.inpaint(cc, deviation_mask(cc.astype(np.float32) / 255.0, C_TEXT, thresh=0.02, dilate=9),
                     8, cv2.INPAINT_TELEA)
    cc = melt(cc, C_TEXT, sigma_soft=15, sigma_w=7)
    save_plate(cc, "gji-hall")

    print("emblem:")
    cx, cy, r = B_COIN["cx"], B_COIN["cy"], B_COIN["r"]
    pad = 34
    x0, y0, x1, y1 = cx - r - pad, cy - r - pad, cx + r + pad, cy + r + pad
    crop = b[y0:y1, x0:x1].astype(np.float32) / 255.0
    h, w, _ = crop.shape
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.sqrt((xx - (cx - x0)) ** 2 + (yy - (cy - y0)) ** 2)
    alpha = np.clip((r + 18 - dist) / 26.0, 0, 1)          # solid coin, soft glow rim
    rgba = np.dstack([np.clip(crop * 255, 0, 255).astype(np.uint8),
                      np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    im.save(os.path.join(OUT, "gji-emblem.webp"), "WEBP", quality=92, method=6)
    im.save(os.path.join(OUT, "gji-emblem.png"), "PNG", optimize=True)
    print(f"  gji-emblem {im.size[0]}x{im.size[1]}")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
