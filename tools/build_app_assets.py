"""
Geetha Jewellers - SECTION 11 (App Download + Footer) assets
------------------------------------------------------------
    python tools/build_app_assets.py

Input: additional reference image11.png (1024x1536).

Outputs (images/)
    gja-scene.webp/.png   the phones-on-podium composition (podium engraving
                          + margin annotations lifted to HTML; left/top edges
                          feathered so the plate melts into the cream band)
    gja-qr.png            the QR card (decorative - no app links exist yet)
    gja-mono.webp/.png    the GJ monogram, alpha-keyed from the footer
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

SCENE = (470, 50, 1024, 905)
INPAINT = [
    (918, 52, 1008, 88),      # ornament above the margin annotation
    (922, 92, 1018, 175),     # LUXURY / ANYTIME / ANYWHERE
    (935, 178, 956, 224),     # its vertical rule (stops above the phone corner)
    (468, 792, 502, 862),     # tail of the left-column quote crossing the scene edge
    (618, 726, 806, 816),     # podium engraving TRADITION / NOW A TAP AWAY
]
QR = (60, 780, 168, 888)
MONO = (50, 1150, 158, 1224)


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


def main():
    img = np.asarray(Image.open(os.path.join(SPEC, "image11.png")).convert("RGB"))
    rgb = img.astype(np.float32) / 255.0

    clean = cv2.inpaint(img, deviation_mask(rgb, INPAINT), 8, cv2.INPAINT_TELEA)
    clean = cv2.inpaint(clean, deviation_mask(clean.astype(np.float32) / 255.0,
                                              [INPAINT[4]], thresh=0.022, dilate=7),
                        8, cv2.INPAINT_TELEA)
    clean = melt(clean, INPAINT)

    print("scene:")
    x0, y0, x1, y1 = SCENE
    crop = clean[y0:y1, x0:x1].astype(np.float32)
    h, w, _ = crop.shape
    a = np.ones((h, w), np.float32)
    f = 42
    ramp = np.linspace(0, 1, f)
    a[:, :f] *= ramp[None, :]          # left edge melts into the cream band
    a[:30, :] *= np.linspace(0, 1, 30)[:, None]
    rgba = np.dstack([np.clip(crop, 0, 255).astype(np.uint8),
                      np.clip(a * 255, 0, 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA")
    im = im.resize((round(w * 1.6), round(h * 1.6)), Image.LANCZOS)
    im.save(os.path.join(OUT, "gja-scene.webp"), "WEBP", quality=88, method=6)
    im.save(os.path.join(OUT, "gja-scene.png"), "PNG", optimize=True)
    print(f"  gja-scene {im.size[0]}x{im.size[1]}")

    print("qr:")
    x0, y0, x1, y1 = QR
    q = Image.fromarray(img[y0:y1, x0:x1])
    q = q.resize((q.width * 2, q.height * 2), Image.LANCZOS)
    q.save(os.path.join(OUT, "gja-qr.png"), "PNG", optimize=True)
    print(f"  gja-qr    {q.size[0]}x{q.size[1]}")

    print("monogram:")
    x0, y0, x1, y1 = MONO
    mc = rgb[y0:y1, x0:x1]
    bg = np.median(mc.reshape(-1, 3), axis=0)
    dist = np.abs(mc - bg[None, None, :]).max(axis=2)
    alpha = np.clip((dist - 0.02) * 9, 0, 1)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)
    rgba = np.dstack([np.clip(mc * 255, 0, 255).astype(np.uint8),
                      np.clip(alpha * 255, 0, 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    im.save(os.path.join(OUT, "gja-mono.webp"), "WEBP", quality=92, method=6)
    im.save(os.path.join(OUT, "gja-mono.png"), "PNG", optimize=True)
    print(f"  gja-mono  {im.size[0]}x{im.size[1]}")

    for name, (x, y) in {"band": (200, 620), "more": (60, 1000), "panel": (500, 1000),
                         "footer": (500, 1460)}.items():
        print(f"  sample {name:7s}", img[y, x])
    print("done ->", OUT)


if __name__ == "__main__":
    main()
