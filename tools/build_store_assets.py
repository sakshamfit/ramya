"""
Geetha Jewellers - SECTION 10 (Visit Our Store) assets
------------------------------------------------------
    python tools/build_store_assets.py

Input: reference keyframe 10 (1536x864).

Outputs (images/)
    gjv-store.webp/.png   the framed storefront photograph (gold frame + the
                          map pin on its corner baked; polygon alpha)
    gjv-orn-l.*           left-edge gold mandala ornaments (feathered)
    gjv-orn-r.*           the mandala right of the frame
    gjv-fol-l.*           bottom-left foliage (panel-overlap pixels dropped)
    gjv-fol-r.*           bottom-right soft leaf shadows
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

STORE_POLY = [(614, 242), (1262, 158), (1262, 128), (1316, 128),
              (1316, 809), (1288, 814), (612, 788)]


def save_rgba(rgb, alpha, name, scale=1.5):
    ys, xs = np.where(alpha > 0.01)
    pad = 2
    y0, y1 = max(0, ys.min() - pad), min(alpha.shape[0], ys.max() + pad + 1)
    x0, x1 = max(0, xs.min() - pad), min(alpha.shape[1], xs.max() + pad + 1)
    crop, a = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
    out = crop.copy()
    out[a < 0.002] = 1.0
    rgba = np.dstack([np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8),
                      np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA")
    if scale != 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    im.save(os.path.join(OUT, f"{name}.webp"), "WEBP", quality=90, method=6)
    im.save(os.path.join(OUT, f"{name}.png"), "PNG", optimize=True)
    print(f"  {name:10s} {im.size[0]}x{im.size[1]}")
    return (x0, y0, x1, y1)


def feather_rect(shape, box, f=24, solid_edges=()):
    """rect alpha with linear fades on non page-edge sides"""
    x0, y0, x1, y1 = box
    a = np.zeros(shape, np.float32)
    a[y0:y1, x0:x1] = 1.0
    ramp = np.linspace(0, 1, f)
    if "top" not in solid_edges:
        a[y0:y0 + f, x0:x1] *= ramp[:, None]
    if "bottom" not in solid_edges:
        a[y1 - f:y1, x0:x1] *= ramp[::-1][:, None]
    if "left" not in solid_edges:
        a[y0:y1, x0:x0 + f] *= ramp[None, :]
    if "right" not in solid_edges:
        a[y0:y1, x1 - f:x1] *= ramp[::-1][None, :]
    return a


def main():
    img = np.asarray(Image.open(os.path.join(SPEC, "image10.jpeg")).convert("RGB"))
    rgb = img.astype(np.float32) / 255.0
    h, w, _ = rgb.shape
    manifest = {}

    print("storefront:")
    m = np.zeros((h, w), np.float32)
    cv2.fillPoly(m, [np.array(STORE_POLY, np.int32)], 1.0)
    m = np.clip(cv2.GaussianBlur(m, (0, 0), 1.4), 0, 1)
    bx0, by0, bx1, by1 = save_rgba(rgb, m, "gjv-store")
    manifest["store"] = {"left": round(bx0 / SCENE_W, 4), "top": round(by0 / SCENE_H, 4),
                         "w": round((bx1 - bx0) / SCENE_W, 4), "h": round((by1 - by0) / SCENE_H, 4)}

    print("decor:")
    a = feather_rect((h, w), (0, 285, 146, 675), 24, solid_edges=("left",))
    b = save_rgba(rgb, a, "gjv-orn-l")
    manifest["ornL"] = {"left": round(b[0] / SCENE_W, 4), "top": round(b[1] / SCENE_H, 4),
                        "w": round((b[2] - b[0]) / SCENE_W, 4)}

    a = feather_rect((h, w), (1317, 222, 1402, 352), 18)
    b = save_rgba(rgb, a, "gjv-orn-r")
    manifest["ornR"] = {"left": round(b[0] / SCENE_W, 4), "top": round(b[1] / SCENE_H, 4),
                        "w": round((b[2] - b[0]) / SCENE_W, 4)}

    a = feather_rect((h, w), (0, 688, 340, 864), 26, solid_edges=("left", "bottom"))
    a[688:786, 153:340] = 0            # never bake the dark panel corner
    a[770:786, 153:340] *= 0           # (kept zero; feather below handles the seam)
    a = np.clip(cv2.GaussianBlur(a, (0, 0), 5), 0, 1)
    b = save_rgba(rgb, a, "gjv-fol-l")
    manifest["folL"] = {"left": round(b[0] / SCENE_W, 4), "top": round(b[1] / SCENE_H, 4),
                        "w": round((b[2] - b[0]) / SCENE_W, 4)}

    a = feather_rect((h, w), (1320, 745, 1536, 864), 26, solid_edges=("right", "bottom"))
    b = save_rgba(rgb, a, "gjv-fol-r")
    manifest["folR"] = {"left": round(b[0] / SCENE_W, 4), "top": round(b[1] / SCENE_H, 4),
                        "w": round((b[2] - b[0]) / SCENE_W, 4)}

    for name, (x, y) in {"top": (760, 22), "mid": (420, 120), "right": (1500, 430),
                         "bottom": (900, 850), "panelbg": (300, 400)}.items():
        print(f"  sample {name:8s}", img[y, x])

    with open(os.path.join(OUT, "gjv-manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
