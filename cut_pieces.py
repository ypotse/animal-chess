#!/usr/bin/env python3
"""
Cut pieces from pieces.png into 200x200 individual PNGs.

Strategy:
  Each sprite occupies a 256x256 cell but the circle border often extends
  past the cell edge into neighbouring cells.  We fit the circle using only
  the arc pixels that are safely inside the cell (>= EDGE_SAFE pixels from
  each potentially-clipped edge), then sample the full image with an extended
  window to get the complete bitmap.

Layout (4 cols × 4 rows, 256 px each):
  row 0: red   — elephant, lion, tiger, leopard
  row 1: red   — wolf, dog, cat, rat
  row 2: black — elephant, lion, tiger, leopard
  row 3: black — wolf, dog, cat, rat
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

# (col, row) within the 4x4 grid
LAYOUT = [
    # (player, animal, col, row)  — 4 cols × 4 rows, 256 px cells
    # Row 0 = red top row,   Row 2 = black top row
    ('red',   'elephant', 0, 0), ('red',   'tiger',   1, 0),
    ('red',   'cat',      2, 0), ('red',   'wolf',    3, 0),
    ('red',   'dog',      0, 1), ('red',   'rat',     1, 1),
    ('red',   'leopard',  2, 1), ('red',   'lion',    3, 1),
    ('black', 'elephant', 0, 2), ('black', 'tiger',   1, 2),
    ('black', 'cat',      2, 2), ('black', 'wolf',    3, 2),
    ('black', 'dog',      0, 3), ('black', 'rat',     1, 3),
    ('black', 'leopard',  2, 3), ('black', 'lion',    3, 3),
]

EDGE_SAFE = 20   # pixels from each edge to trust as "our circle" arc
DARK_THRESH = 90


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


def collect_arc_points(bright, clipped_right, clipped_left, clipped_top, clipped_bot):
    """
    Collect boundary arc points from each edge-scan direction,
    skipping directions where the arc is clipped by the cell boundary.
    """
    H, W = bright.shape
    cols = np.arange(W)
    rows = np.arange(H)
    pts = []

    # Left arc (leftmost dark per row) — skip if circle clipped on left
    if not clipped_left:
        for row in rows:
            darks = np.where(bright[row] < DARK_THRESH)[0]
            if len(darks):
                pts.append((float(darks[0]), float(row)))

    # Right arc (rightmost dark per row, capped at safe zone) — skip if clipped right
    if not clipped_right:
        for row in rows:
            darks = np.where(bright[row] < DARK_THRESH)[0]
            if len(darks):
                pts.append((float(darks[-1]), float(row)))
    else:
        # Still use right arc but only trust pixels far from right edge
        safe = W - EDGE_SAFE
        for row in rows:
            darks = np.where((bright[row] < DARK_THRESH) & (cols < safe))[0]
            if len(darks):
                pts.append((float(darks[-1]), float(row)))

    # Top arc (topmost dark per col) — skip if clipped on top
    if not clipped_top:
        for col in cols:
            darks = np.where(bright[:, col] < DARK_THRESH)[0]
            if len(darks):
                pts.append((float(col), float(darks[0])))

    # Bottom arc (bottommost dark per col) — skip if clipped on bottom
    if not clipped_bot:
        for col in cols:
            darks = np.where(bright[:, col] < DARK_THRESH)[0]
            if len(darks):
                pts.append((float(col), float(darks[-1])))

    return np.array(pts) if pts else None


for player, animal, sc, sr in LAYOUT:
    sx, sy = sc * SPR, sr * SPR
    sprite = arr[sy:sy+SPR, sx:sx+SPR, :3].astype(float)
    bright = sprite.mean(axis=2)

    # Detect which edges have significant dark-pixel presence (clipped)
    CLIP_THRESH = 40
    right_ct = sum(1 for r in range(SPR) if np.any(bright[r, SPR-EDGE_SAFE:] < DARK_THRESH))
    left_ct  = sum(1 for r in range(SPR) if np.any(bright[r, :EDGE_SAFE] < DARK_THRESH))
    top_ct   = sum(1 for c in range(SPR) if np.any(bright[:EDGE_SAFE, c] < DARK_THRESH))
    bot_ct   = sum(1 for c in range(SPR) if np.any(bright[SPR-EDGE_SAFE:, c] < DARK_THRESH))

    clipped_right = right_ct > CLIP_THRESH
    clipped_left  = left_ct  > CLIP_THRESH
    clipped_top   = top_ct   > CLIP_THRESH
    clipped_bot   = bot_ct   > CLIP_THRESH

    pts = collect_arc_points(bright, clipped_right, clipped_left, clipped_top, clipped_bot)
    if pts is None or len(pts) < 8:
        print(f"WARNING: {player} {animal} — not enough arc points, falling back")
        ys_d, xs_d = np.where(bright < DARK_THRESH)
        pts = np.c_[xs_d.astype(float), ys_d.astype(float)]

    cx_cell, cy_cell, r = fit_circle(pts[:, 0], pts[:, 1])

    clipped_info = (
        ("R" if clipped_right else "") +
        ("L" if clipped_left  else "") +
        ("T" if clipped_top   else "") +
        ("B" if clipped_bot   else "")
    )
    print(f"{player:5} {animal:10}: centre=({cx_cell:.1f},{cy_cell:.1f}) r={r:.1f}  clipped={clipped_info or 'none'}")

    # Extract a padded window from the full image to capture the whole circle.
    # IMPORTANT: clamp the extraction to the original sprite cell boundary only.
    # Neighbouring sprites have their own dark circle borders — pulling pixels
    # beyond the cell boundary causes those borders to appear in our output.
    cx_full = sx + cx_cell
    cy_full = sy + cy_cell
    PAD = 4
    ex0 = max(sx,        int(cx_full - r) - PAD)
    ey0 = max(sy,        int(cy_full - r) - PAD)
    ex1 = min(sx + SPR,  int(cx_full + r) + PAD + 1)
    ey1 = min(sy + SPR,  int(cy_full + r) + PAD + 1)

    region = Image.fromarray(arr[ey0:ey1, ex0:ex1]).convert("RGBA")
    rW = ex1 - ex0
    rH = ey1 - ey0

    # Scale so circle fills OUT-4 pixels (2px margin each side)
    scale = (OUT - 4) / (2 * r)
    sw = max(OUT, int(rW * scale + 0.5))
    sh = max(OUT, int(rH * scale + 0.5))
    scaled = region.resize((sw, sh), Image.LANCZOS)

    # Circle centre in scaled image
    scx = (cx_full - ex0) * scale
    scy = (cy_full - ey0) * scale

    # Crop OUT×OUT centred on circle
    crop_l = max(0, int(scx - OUT // 2))
    crop_t = max(0, int(scy - OUT // 2))
    crop_l = min(crop_l, max(0, sw - OUT))
    crop_t = min(crop_t, max(0, sh - OUT))

    cropped = scaled.crop((crop_l, crop_t, crop_l + OUT, crop_t + OUT)).convert("RGBA")

    # Circular alpha mask with slight feathering
    mask = Image.new("L", (OUT, OUT), 0)
    ImageDraw.Draw(mask).ellipse((2, 2, OUT - 3, OUT - 3), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1))
    cropped.putalpha(mask)

    out_path = f"assets/piece_{player}_{animal}.png"
    cropped.save(out_path)

print("\nDone — saved 16 PNGs to assets/")
