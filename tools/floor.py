"""
Glossy-floor reconstruction shared by the collection-plate builders
-------------------------------------------------------------------
The reference keyframes hide part of their marble floor under detail cards
and thumbnail rails. Lifting those out leaves holes, and a diffusion inpaint
or a vertical blend turns such a wide hole into a smeared band that reads as
a blurred screen. The holes are rebuilt instead the way the floor is actually
formed:

  * a smooth base that follows the surrounding REAL floor - a mask-weighted,
    strongly horizontal average (a floor varies along the room, not down it),
    read only from pixels outside the holes;
  * a faint, fading mirror of whatever stands above the floor line (podium,
    rim, columns), squashed and softened the way a polished floor reflects -
    added as structure only, so the base's tone is untouched;
  * a hair of dither so the smooth gradient never bands in 8-bit.

Nothing real is blurred; the fill is only ever written inside the holes.
"""
from __future__ import annotations

import cv2
import numpy as np


def _normconv(img, weight, sx, sy):
    num = cv2.GaussianBlur(img * weight[..., None], (0, 0), sigmaX=sx, sigmaY=sy)
    den = cv2.GaussianBlur(weight, (0, 0), sigmaX=sx, sigmaY=sy)
    return num / np.maximum(den[..., None], 1e-6), den


def disc_mask(shape, discs):
    m = np.zeros(shape[:2], np.uint8)
    for cx, cy, r in discs:
        cv2.circle(m, (int(cx), int(cy)), int(r), 255, -1)
    return m


def rect_mask(shape, rects, grow=0):
    m = np.zeros(shape[:2], np.uint8)
    for x0, y0, x1, y1 in rects:
        m[max(0, y0 - grow):y1 + grow, max(0, x0 - grow):x1 + grow] = 255
    return m


def poly_mask(shape, points):
    m = np.zeros(shape[:2], np.uint8)
    cv2.fillPoly(m, [np.array(points, np.int32)], 255)
    return m


def dark_mask(rgb, boxes, thresh=0.035, sigma=13, dilate=7):
    """Strokes DARKER than the local floor inside `boxes` (labels, rules, dots,
    card shadows). Bright things - bokeh blossoms, silk highlights, glass rims -
    never trigger it, so real props next to the text survive untouched."""
    bg = cv2.GaussianBlur(rgb, (0, 0), sigma)
    dev = (bg - rgb).max(axis=2)
    m = np.zeros(rgb.shape[:2], np.uint8)
    for (x0, y0, x1, y1) in boxes:
        sub = dev[y0:y1, x0:x1] > thresh
        m[y0:y1, x0:x1] = np.maximum(m[y0:y1, x0:x1], sub.astype(np.uint8) * 255)
    return cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate, dilate)))


def synth_floor(img, holes, box, floor_line, exclude=None, mirror=0.6, squash=0.72,
                fade=0.62, sx=26, sy=7, mode="structure", feather=2.0, dither=0.5 / 255):
    """Rebuild `holes` (uint8, 255 = rebuild) inside `box` on a float32 RGB image.

    img:        HxWx3 float32, 0..1 or 0..255 (returned in the same range)
    floor_line: y of the floor/podium contact; the scene above it is mirrored
                downward as the polished-floor reflection
    exclude:    optional mask of pixels neither rebuilt nor trusted as floor
                samples (props, silk, blossoms - real things that stay as they are)
    mode:       "structure" adds only the mirror's edges/detail to the base (for a
                band whose real gaps already carry the reflection's brightness);
                "full" composites the softened mirror itself, fading downward
                (for a band rebuilt as one piece, where the base alone would
                miss the bright reflection under the podium)
    feather:    sigma of the blend on the real side of every hole edge
    """
    scale = 255.0 if img.max() > 1.5 else 1.0
    H, W = img.shape[:2]
    x0, y0, x1, y1 = box
    pad = 140
    cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
    cx1, cy1 = min(W, x1 + pad), min(H, y1 + pad)
    sub = img[cy0:cy1, cx0:cx1].astype(np.float32) / scale
    hole = holes[cy0:cy1, cx0:cx1] > 0
    if exclude is not None:
        excl = exclude[cy0:cy1, cx0:cx1] > 0
        hole &= ~excl
    trust = ~hole
    if exclude is not None:
        trust &= ~excl
    w = trust.astype(np.float32)

    # base: a cascade of horizontal mask-weighted averages; each finer level is
    # trusted only where enough of its kernel mass fell on real floor pixels
    b1, d1 = _normconv(sub, w, sx, sy)
    b2, d2 = _normconv(sub, w, sx * 4.2, sy * 1.8)
    b3, _ = _normconv(sub, w, sx * 9.0, sy * 7.0)
    w1 = np.clip(d1 / 0.12, 0, 1)[..., None]
    w2 = np.clip(d2 / 0.12, 0, 1)[..., None]
    base = b1 * w1 + (1 - w1) * (b2 * w2 + (1 - w2) * b3)

    # reflection: what stands above the floor line, mirrored + squashed, softened
    # a touch more vertically than horizontally (polished stone, not a mirror)
    fl = floor_line - cy0
    span = sub.shape[0] - fl
    src_h = int(np.ceil(span / squash))
    above = sub[max(0, fl - src_h):fl][::-1]
    refl = cv2.resize(above, (sub.shape[1], max(1, int(above.shape[0] * squash))), interpolation=cv2.INTER_AREA)
    refl = cv2.GaussianBlur(refl, (0, 0), sigmaX=1.2, sigmaY=3.5)
    n = min(span, refl.shape[0])
    yy = np.arange(sub.shape[0], dtype=np.float32)[:, None, None]
    fadev = np.clip(1 - (yy - fl) / (fade * span), 0, 1) ** 1.6
    fadev[yy < fl] = 0
    if mode == "full":
        mirrored = base.copy()
        mirrored[fl:fl + n] = refl[:n]
        m = mirror * fadev
        fill = base * (1 - m) + mirrored * m
    else:
        hp = refl - cv2.GaussianBlur(refl, (0, 0), 14)
        detail = np.zeros_like(sub)
        detail[fl:fl + n] = hp[:n]
        fill = base + detail * mirror * fadev
    if dither:
        fill = fill + np.random.default_rng(7).normal(0, dither, fill.shape).astype(np.float32)

    # every hole pixel is fully rebuilt; the real side gets a feathered blend
    a = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), feather)[..., None]
    a = np.where(hole[..., None], 1.0, a)
    out = img.astype(np.float32).copy()
    out[cy0:cy1, cx0:cx1] = np.clip(sub * (1 - a) + fill * a, 0, 1) * scale
    return out
