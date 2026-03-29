#!/usr/bin/env python3
"""
Cut each piece from pieces.png into individual circle-masked PNGs.
Saves to assets/ folder.
"""
from PIL import Image, ImageDraw
import numpy as np
import os

os.makedirs("assets", exist_ok=True)

p = Image.open("pieces.png").convert("RGBA")
arr = np.array(p)
SPR = 256   # sprite cell size
OUT = 200   # output size

# Sprite grid layout (col, base_row) by animal name
PIECES = {
    'elephant': (0, 0),
    'tiger':    (1, 0),
    'cat':      (2, 0),
    'wolf':     (3, 0),
    'dog':      (0, 1),
    'rat':      (1, 1),
    'leopard':  (2, 1),
    'lion':     (3, 1),
}
PLAYERS = [('red', 0), ('black', 2)]

def find_circle(sprite_arr):
    """Find circle centre and radius in a sprite by scanning edges."""
    # Non-white = any channel < 230
    mask = np.any(sprite_arr[:, :, :3] < 230, axis=2)
    ys, xs = np.where(mask)
    if not len(xs):
        return SPR//2, SPR//2, SPR//2
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    cx = (x0 + x1) / 2
    cy = (y0 + y1) / 2
    # Use the smaller of width/height halves as radius (handles clipped sprites at edge)
    r = min((x1 - x0) / 2, (y1 - y0) / 2)
    return cx, cy, r

saved = []
for animal, (sc, sbr) in PIECES.items():
    for player, row_offset in PLAYERS:
        sr = sbr + row_offset
        sx, sy = sc * SPR, sr * SPR
        sprite = arr[sy:sy+SPR, sx:sx+SPR]

        cx, cy, radius = find_circle(sprite)
        print(f"{player:5} {animal:10}: circle centre ({cx:.1f},{cy:.1f}) r={radius:.1f}")

        # Scale factor: map circle radius → (OUT/2 - 2px margin)
        target_r = OUT / 2 - 2
        scale    = target_r / radius
        new_size = int(round(SPR * scale))

        # Paste scaled sprite onto a white canvas the same size
        spr_img   = Image.fromarray(sprite)
        spr_scaled = spr_img.resize((new_size, new_size), Image.LANCZOS)

        # New circle centre after scaling
        ncx = cx * scale
        ncy = cy * scale

        # Destination canvas (OUT × OUT), centre of canvas = (OUT/2, OUT/2)
        out = Image.new("RGBA", (OUT, OUT), (255, 255, 255, 255))
        paste_x = int(round(OUT/2 - ncx))
        paste_y = int(round(OUT/2 - ncy))
        out.paste(spr_scaled, (paste_x, paste_y))

        # Apply circular alpha mask centred in output canvas
        mask_img = Image.new("L", (OUT, OUT), 0)
        draw = ImageDraw.Draw(mask_img)
        draw.ellipse([2, 2, OUT-3, OUT-3], fill=255)
        # Feather using a slightly smaller inner region (anti-alias)
        r_arr = np.array(mask_img, dtype=np.uint8)
        out_arr = np.array(out)
        out_arr[:, :, 3] = r_arr
        result = Image.fromarray(out_arr)

        fname = f"assets/piece_{player}_{animal}.png"
        result.save(fname)
        saved.append(fname)

print(f"\nSaved {len(saved)} piece PNGs to assets/")
