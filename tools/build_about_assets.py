"""
Geetha Jewellers - SECTION 01 (Our Story / About) asset build
-------------------------------------------------------------
    python tools/build_about_assets.py

Input
    Reference keyframe 01 from the Phase-02 spec docx (word/media/image1.jpeg),
    extracted to the scratchpad. Pass a different path as argv[1] if needed.

Outputs (images/)
    about-scene.webp/.jpg   left jewellery composition (maroon busts, temple light),
                            with every baked-in text overlay removed - the brand
                            lockup, scroll cue and 'explore the craft' annotation
                            are rebuilt as real HTML on top
    about-panel.webp/.jpg   right ivory-marble panel with the gold florals kept and
                            the baked-in text / cards / CTA removed (rebuilt in HTML)

The overlays are removed with a deviation matte (strokes differ from the local
blurred background) inside hand-measured boxes, then Telea inpainting - the
photographic content underneath is untouched.
"""
from __future__ import annotations

import os
import sys

import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images")
DEFAULT_SRC = (r"C:/Users/giris/AppData/Local/Temp/claude/C--Users-giris-OneDrive-Desktop-Geeta"
               r"/b7ef71c2-ecc4-4bf6-b625-7d327dcc1e84/scratchpad/spec/unpacked/word/media/image1.jpeg")

# boxes in source coordinates (1536 x 513)
SCENE_CROP = (0, 0, 1015, 513)
SCENE_OVERLAYS = [
    (88, 26, 415, 302),     # TIMELESS CRAFTSMANSHIP / GEETHA JEWELLERS / SINCE 1998 / italic line
    (20, 330, 198, 487),    # SCROLL TO EXPLORE cue (line, circle, text)
    (632, 200, 734, 246),   # EXPLORE THE CRAFT label
    (636, 242, 852, 322),   # hotspot circle, connector lines, faint scribble
]
PANEL_CROP = (980, 0, 1536, 513)
PANEL_CLEAR = [               # full boxes - text sits on smooth ivory marble
    (983, 40, 1400, 74),      # OUR STORY eyebrow + arrow
    (983, 74, 1482, 136),     # headline + right dash
    (983, 136, 1468, 268),    # body paragraphs
    (981, 271, 1497, 447),    # three value cards (incl. soft shadows + arrow chips)
    (1100, 452, 1516, 492),   # rule + DISCOVER OUR JOURNEY
]


def u8(a):
    return np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8)


def deviation_mask(rgb, boxes, thresh=0.045, sigma=13, dilate=7):
    """Pixels that differ from the locally blurred background inside the boxes."""
    h, w, _ = rgb.shape
    bg = cv2.GaussianBlur(rgb, (0, 0), sigma)
    dev = np.abs(rgb - bg).max(axis=2)
    m = np.zeros((h, w), np.uint8)
    for (x0, y0, x1, y1) in boxes:
        sub = dev[y0:y1, x0:x1] > thresh
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], sub.astype(np.uint8) * 255)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate, dilate))
    return cv2.dilate(m, k)


def box_mask(shape, boxes):
    m = np.zeros(shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        m[y0:y1, x0:x1] = 255
    return m


def save(im: Image.Image, name: str, q_webp=88, q_jpg=88):
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=q_webp, method=6)
    im.save(os.path.join(OUT, f"{name}.jpg"), "JPEG", quality=q_jpg, optimize=True, progressive=True)
    print(f"  {name:14s} {im.size[0]}x{im.size[1]}")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.exists(src):
        sys.exit(f"missing reference keyframe: {src}")
    os.makedirs(OUT, exist_ok=True)
    rgb = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
    img8 = u8(rgb)

    # scene: stroke-level inpaint so the photographic content underneath survives
    m1 = deviation_mask(rgb, SCENE_OVERLAYS)
    clean = cv2.inpaint(img8, m1, 8, cv2.INPAINT_TELEA)
    # panel: full boxes on smooth marble; the fill is then heavily smoothed so no
    # angular Telea seams survive (the marble there is a soft gradient anyway)
    m2 = box_mask(rgb.shape, PANEL_CLEAR)
    clean = cv2.inpaint(clean, m2, 10, cv2.INPAINT_TELEA)
    soft = cv2.GaussianBlur(clean.astype(np.float32), (0, 0), 21)
    w = cv2.GaussianBlur((m2 > 0).astype(np.float32), (0, 0), 6)[..., None]
    clean = np.clip(clean.astype(np.float32) * (1 - w) + soft * w, 0, 255).astype(np.uint8)

    x0, y0, x1, y1 = SCENE_CROP
    save(Image.fromarray(clean[y0:y1, x0:x1]), "about-scene")

    x0, y0, x1, y1 = PANEL_CROP
    panel = Image.fromarray(clean[y0:y1, x0:x1])
    # smooth gradient art upscales cleanly; mild sharpen keeps the florals crisp
    panel = panel.resize((int(panel.size[0] * 1.5), int(panel.size[1] * 1.5)), Image.LANCZOS)
    p = np.asarray(panel).astype(np.float32)
    blur = cv2.GaussianBlur(p, (0, 0), 1.1)
    wk = box_mask(rgb.shape, PANEL_CLEAR)[y0:y1, x0:x1]
    wk = cv2.resize(wk, panel.size, interpolation=cv2.INTER_LINEAR).astype(np.float32)[..., None] / 255.0
    panel = Image.fromarray(np.clip(p + (p - blur) * 0.3 * (1 - wk), 0, 255).astype(np.uint8))
    save(panel, "about-panel", q_webp=86, q_jpg=86)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
