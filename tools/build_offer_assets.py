"""
Geetha Jewellers - SECTION 09 (Offer / Testimonials / Why Choose Us) assets
---------------------------------------------------------------------------
    python tools/build_offer_assets.py

Input: reference keyframe 09 (897x1536 editorial page mock).

Outputs (images/)
    gjo-a.webp/.jpg    offer band plate (copy, badge + box engraving inpainted;
                       rings/marble/ribbon/flowers stay photographic)
    gjo-am.*           mobile crop of the offer visual (right side)
    gjo-d.webp/.jpg    consultation band plate (copy + panel text inpainted,
                       GJ monogram preserved)
    gjo-dm.*           mobile crop of the marble panel side
    gjo-fl/-fr.png     soft testimonial flowers (feathered cutouts)
"""
from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
SPEC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
        r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media")

# ---- text/badge regions to lift into live HTML (src px, 897x1536)
BOXES_A = [
    (60, 52, 280, 80),      # eyebrow + line
    (58, 82, 380, 180),     # FLAT 50 % OFF
    (58, 176, 310, 204),    # ON MAKING CHARGES
    (58, 200, 375, 232),    # rule + REAL DIAMOND JEWELLERY
    (58, 238, 300, 295),    # body copy
    (60, 305, 270, 345),    # CTA button
    (75, 360, 395, 440),    # trust icon row
    (735, 28, 856, 143),    # limited-time badge
]
BOX_ENGRAVE = (540, 338, 700, 430)          # marble-box engraving (low contrast)
BOXES_D = [
    (72, 1240, 270, 1258),  # eyebrow
    (72, 1262, 330, 1338),  # headline
    (72, 1342, 350, 1382),  # body
    (64, 1382, 442, 1442),  # buttons (frosted edges bleed a little wider)
    (72, 1448, 425, 1495),  # mini items
]
BOX_BRAND = [(596, 1315, 790, 1352), (600, 1355, 788, 1382)]  # panel text (keep monogram above)

A_BAND = (0, 0, 897, 456)
A_MOB = (400, 10, 897, 456)
D_BAND = (0, 1212, 897, 1536)
D_MOB = (450, 1212, 897, 1536)
FLOWER_L = (0, 578, 132, 792)
FLOWER_R = (788, 572, 897, 802)


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


def melt(img, boxes, sigma_soft=15, sigma_w=6):
    """soften TELEA streaks inside the filled regions"""
    hole = np.zeros(img.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        hole[max(0, y0 - 4):y1 + 4, max(0, x0 - 4):x1 + 4] = 255
    soft = cv2.GaussianBlur(img.astype(np.float32), (0, 0), sigma_soft)
    w = cv2.GaussianBlur((hole > 0).astype(np.float32), (0, 0), sigma_w)[..., None]
    return np.clip(img.astype(np.float32) * (1 - w) + soft * w, 0, 255).astype(np.uint8)


def save_plate(arr, name, scale=1.6, q=86):
    im = Image.fromarray(arr)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=q, method=6)
    im.save(os.path.join(OUT, f"{name}.jpg"), "JPEG", quality=q, optimize=True, progressive=True)
    print(f"  {name:8s} {im.size[0]}x{im.size[1]}")


def save_flower(img, box, name, page_edge):
    x0, y0, x1, y1 = box
    crop = img[y0:y1, x0:x1].astype(np.float32)
    h, w, _ = crop.shape
    a = np.ones((h, w), np.float32)
    f = 24
    ramp = np.linspace(0, 1, f)
    a[:f] *= ramp[:, None]
    a[-f:] *= ramp[::-1][:, None]
    if page_edge == "left":
        a[:, -f:] *= ramp[::-1][None, :]
    else:
        a[:, :f] *= ramp[None, :]
    rgba = np.dstack([crop, a * 255]).astype(np.uint8)
    im = Image.fromarray(rgba, "RGBA")
    im = im.resize((round(w * 1.6), round(h * 1.6)), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.png"), "PNG", optimize=True)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=90, method=6)
    print(f"  {name:8s} {im.size[0]}x{im.size[1]}")


def main():
    src = os.path.join(SPEC, "image9.jpeg")
    img = np.asarray(Image.open(src).convert("RGB"))
    rgb = img.astype(np.float32) / 255.0

    boxes = BOXES_A + BOXES_D + BOX_BRAND + [BOX_ENGRAVE]
    clean = cv2.inpaint(img, deviation_mask(rgb, boxes), 8, cv2.INPAINT_TELEA)
    # engraved marble + panel text are low-contrast: second pass digs them out
    clean = cv2.inpaint(clean, deviation_mask(clean.astype(np.float32) / 255.0,
                                              [BOX_ENGRAVE] + BOX_BRAND, thresh=0.022, dilate=7),
                        8, cv2.INPAINT_TELEA)
    # melt everywhere EXCEPT the marble faces - their veining must stay crisp
    clean = melt(clean, BOXES_A + BOXES_D, sigma_soft=15, sigma_w=9)

    print("plates:")
    x0, y0, x1, y1 = A_BAND
    save_plate(clean[y0:y1, x0:x1], "gjo-a")
    x0, y0, x1, y1 = A_MOB
    save_plate(clean[y0:y1, x0:x1], "gjo-am")
    x0, y0, x1, y1 = D_BAND
    save_plate(clean[y0:y1, x0:x1], "gjo-d")
    x0, y0, x1, y1 = D_MOB
    save_plate(clean[y0:y1, x0:x1], "gjo-dm")

    print("flowers:")
    save_flower(img, FLOWER_L, "gjo-fl", "left")
    save_flower(img, FLOWER_R, "gjo-fr", "right")

    for name, (ya, yb) in [("B band", (470, 520)), ("C band", (900, 960))]:
        print(name, "mean rgb:", img[ya:yb, 200:700].reshape(-1, 3).mean(axis=0).round(1))

    print("done ->", OUT)


if __name__ == "__main__":
    main()
