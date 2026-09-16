"""
Geetha Jewellers - HD pass: 2x super-resolution of every site image
-------------------------------------------------------------------
    python tools/hd_upscale.py

Every plate/cutout in images/ is upscaled 2x with FSRCNN (learned
super-resolution, tools/models/FSRCNN_x2.pb) and finished with a light
unsharp mask, then re-encoded at high quality (WebP q92-95, JPEG q92, PNG
lossless). Alpha cutouts are upscaled premultiplied so edges never fringe.
Run this AFTER any tools/build_*_assets.py rebuild (those write native-ish
resolution); images already >= 2400px wide are left alone. Idempotent.
"""
from __future__ import annotations

import os

import cv2
import numpy as np
from PIL import Image, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "images")
MODEL = os.path.join(ROOT, "tools", "models", "FSRCNN_x2.pb")
SKIP = {"favicon-32.png", "apple-touch-icon.png", "gja-qr.png"}
MIN_DONE_WIDTH = 2400

sr = cv2.dnn_superres.DnnSuperResImpl_create()
sr.readModel(MODEL)
sr.setModel("fsrcnn", 2)


def sr2x(rgb_u8: np.ndarray, tile=224, overlap=16) -> np.ndarray:
    """2x super-resolution in overlapping horizontal tiles (keeps peak memory
    small; the network is convolutional, so seams inside the overlap are exact)."""
    bgr = cv2.cvtColor(rgb_u8, cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    out = np.zeros((h * 2, w * 2, 3), np.uint8)
    y = 0
    while y < h:
        y0 = max(0, y - overlap)
        y1 = min(h, y + tile + overlap)
        up = sr.upsample(bgr[y0:y1])
        top = (y - y0) * 2
        take_h = (min(h, y + tile) - y) * 2
        out[y * 2:y * 2 + take_h] = up[top:top + take_h]
        y += tile
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)


def sharpen(im: Image.Image) -> Image.Image:
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=26, threshold=2))


def upscale_rgba(im: Image.Image) -> Image.Image:
    a = np.asarray(im.getchannel("A")).astype(np.float32) / 255.0
    rgb = np.asarray(im.convert("RGB")).astype(np.float32) / 255.0
    prem = np.clip(rgb * a[..., None] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    up = sr2x(prem).astype(np.float32) / 255.0
    w, h = im.size
    a_up = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((w * 2, h * 2), Image.LANCZOS)).astype(np.float32) / 255.0
    rgb_up = np.clip(up / np.maximum(a_up[..., None], 1e-3), 0, 1)
    rgb_up[a_up < 0.004] = 1.0
    rgb_im = sharpen(Image.fromarray((rgb_up * 255 + 0.5).astype(np.uint8), "RGB"))
    out = np.dstack([np.asarray(rgb_im), (a_up * 255 + 0.5).astype(np.uint8)])
    return Image.fromarray(out, "RGBA")


def upscale_rgb(im: Image.Image) -> Image.Image:
    up = sr2x(np.asarray(im.convert("RGB")))
    return sharpen(Image.fromarray(up, "RGB"))


def main():
    import json
    # idempotency: a manifest records each stem's size after its upscale; a
    # file whose current size still matches was not rebuilt and is skipped
    ledger_path = os.path.join(IMG, "hd-upscaled.json")
    ledger = json.load(open(ledger_path)) if os.path.exists(ledger_path) else {}
    files = sorted(os.listdir(IMG))
    stems: dict[str, str] = {}
    for f in files:
        stem, ext = os.path.splitext(f)
        if f in SKIP or ext.lower() not in (".png", ".jpg", ".jpeg"):
            continue
        # prefer the lossless PNG master when both exist
        if stem not in stems or ext.lower() == ".png":
            stems[stem] = f

    done = 0
    for stem, src in stems.items():
        path = os.path.join(IMG, src)
        im = Image.open(path)
        if ledger.get(stem) == [im.width, im.height] or im.width >= MIN_DONE_WIDTH * 1.5:
            print(f"  skip  {src} ({im.width}x{im.height}, already HD)")
            continue
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        if has_alpha:
            out = upscale_rgba(im.convert("RGBA"))
            out.save(os.path.join(IMG, stem + ".png"), "PNG", optimize=True)
            out.save(os.path.join(IMG, stem + ".webp"), "WEBP", quality=95, method=6)
        else:
            out = upscale_rgb(im)
            if src.lower().endswith(".png"):
                out.save(os.path.join(IMG, stem + ".png"), "PNG", optimize=True)
            else:
                out.save(os.path.join(IMG, stem + ".jpg"), "JPEG", quality=92, optimize=True, progressive=True)
            out.save(os.path.join(IMG, stem + ".webp"), "WEBP", quality=92, method=6)
        done += 1
        ledger[stem] = [out.width, out.height]
        json.dump(ledger, open(ledger_path, "w"), indent=1, sort_keys=True)
        print(f"  {stem:22s} {im.width}x{im.height} -> {out.width}x{out.height}", flush=True)
    print(f"done: {done} images upscaled")


if __name__ == "__main__":
    main()
