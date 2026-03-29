#!/usr/bin/env python3
"""
Cut pieces from pieces.png into 200×200 individual PNGs.

Strategy:
  For each 256×256 sprite cell, scan the outermost dark pixel in every row
  and column (left / right / top / bottom boundary), fit a circle to those
  boundary points, then scale and crop so the circle fills the output and
  apply a circular alpha mask.

  Extraction is taken from the full source image (not clamped to the cell)
  so that arcs which marginally spill past the cell edge are included.
  The circular alpha mask then cleanly hides any neighbouring-sprite pixels
  that fall outside our fitted circle radius.

Layout (4 cols × 4 rows, 256 px each):
  row 0: red   — elephant, tiger, cat,  wolf
  row 1: red   — dog,      rat,   leopard, lion
  row 2: black — elephant, tiger, cat,  wolf
  row 3: black — dog,      rat,   leopard, lion
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

os.makedirs("assets", exist_ok=True)

p = Image.open("pieces.png").convert("RGBA")
arr = np.array(p)
ph, pw = arr.shape[:2]
SPR = 256
OUT = 200
DARK = 90   # pixel brightness below which we call it "dark border"

LAYOUT = [
    # (player, animal, col, row)
    ('red',   'elephant', 0, 0), ('red',   'tiger',   1, 0),
    ('red',   'cat',      2, 0), ('red',   'wolf',    3, 0),
    ('red',   'dog',      0, 1), ('red',   'rat',     1, 1),
    ('red',   'leopard',  2, 1), ('red',   'lion',    3, 1),
    ('black', 'elephant', 0, 2), ('black', 'tiger',   1, 2),
    ('black', 'cat',      2, 2), ('black', 'wolf',    3, 2),
    ('black', 'dog',      0, 3), ('black', 'rat',     1, 3),
    ('black', 'leopard',  2, 3), ('black', 'lion',    3, 3),
]


def fit_circle(xs, ys):
    """Kasa algebraic circle fit. Returns (cx, cy, r)."""
    x = xs.astype(float)
    y = ys.astype(float)
    A = np.c_[x * 2, y * 2, np.ones(len(x))]
    b = x**2 + y**2
    res, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = res[0], res[1]
    r = float(np.sqrt(res[2] + cx**2 + cy**2))
    return cx, cy, r


for player, animal, sc, sr in LAYOUT:
    sx, sy = sc * SPR, sr * SPR   # top-left of sprite cell in full image

    # --- fit circle using border arc from within the cell only ---
    sprite = arr[sy:sy+SPR, sx:sx+SPR, :3].astype(float)
    bright  = sprite.mean(axis=2)

    arc_pts = []
    for row in range(SPR):
        darks = np.where(bright[row] < DARK)[0]
        if len(darks):
            arc_pts.append((float(darks[0]),  float(row)))   # leftmost arc
            arc_pts.append((float(darks[-1]), float(row)))   # rightmost arc
    for col in range(SPR):
        darks = np.where(bright[:, col] < DARK)[0]
        if len(darks):
            arc_pts.append((float(col), float(darks[0])))    # topmost arc
            arc_pts.append((float(col), float(darks[-1])))   # bottommost arc

    pts = np.array(arc_pts)
    cx_cell, cy_cell, r = fit_circle(pts[:, 0], pts[:, 1])

    print(f"{player:5} {animal:10}: cx={cx_cell:6.1f} cy={cy_cell:6.1f} r={r:6.1f}")

    # --- extract region from full image, centred on fitted circle ---
    # Don't clamp to cell so marginally-clipped arcs are captured.
    # The circular alpha mask will hide any neighbouring-sprite pixels.
    cx_full = sx + cx_cell
    cy_full = sy + cy_cell
    PAD = 6

    ex0 = max(0,  int(cx_full - r) - PAD)
    ey0 = max(0,  int(cy_full - r) - PAD)
    ex1 = min(pw, int(cx_full + r) + PAD + 1)
    ey1 = min(ph, int(cy_full + r) + PAD + 1)

    region = Image.fromarray(arr[ey0:ey1, ex0:ex1]).convert("RGBA")
    rW = ex1 - ex0
    rH = ey1 - ey0

    # Scale so the fitted circle fills OUT−4 pixels (2 px margin each side)
    scale = (OUT - 4) / (2 * r)
    sw = max(OUT, int(rW * scale + 0.5))
    sh = max(OUT, int(rH * scale + 0.5))
    scaled = region.resize((sw, sh), Image.LANCZOS)

    # Circle centre in scaled image
    scx = (cx_full - ex0) * scale
    scy = (cy_full - ey0) * scale

    # Crop OUT×OUT centred on circle
    crop_l = int(scx - OUT / 2 + 0.5)
    crop_t = int(scy - OUT / 2 + 0.5)
    crop_l = max(0, min(crop_l, sw - OUT))
    crop_t = max(0, min(crop_t, sh - OUT))

    cropped = scaled.crop((crop_l, crop_t, crop_l + OUT, crop_t + OUT)).convert("RGBA")

    # Circular alpha mask with slight feathering
    mask = Image.new("L", (OUT, OUT), 0)
    ImageDraw.Draw(mask).ellipse((2, 2, OUT - 3, OUT - 3), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1))
    cropped.putalpha(mask)

    cropped.save(f"assets/piece_{player}_{animal}.png")

print("\nDone — saved 16 PNGs to assets/")
