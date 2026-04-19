"""Stitch all manual_*_composite.png into one labelled grid."""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

here = Path(__file__).parent
items = sorted(p for p in here.glob("views_manual_*/composite.png"))

# Label = dir name minus "views_manual_"
labels = [p.parent.name.replace("views_manual_", "") for p in items]

TILE = 268  # composite is 268x268
LABEL_H = 28
PAD = 6
COLS = 4
rows = (len(items) + COLS - 1) // COLS

W = COLS * (TILE + PAD) + PAD
H = rows * (TILE + LABEL_H + PAD) + PAD
grid = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(grid)

try:
    font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 14)
except OSError:
    font = ImageFont.load_default()

for i, (path, label) in enumerate(zip(items, labels)):
    r, c = divmod(i, COLS)
    x = PAD + c * (TILE + PAD)
    y = PAD + r * (TILE + LABEL_H + PAD)
    im = Image.open(path).convert("RGB")
    if im.size != (TILE, TILE):
        im = im.resize((TILE, TILE))
    grid.paste(im, (x, y))
    draw.text((x + 4, y + TILE + 4), label, fill="black", font=font)

out = here / "all_manuals_grid.png"
grid.save(out)
print(f"wrote {out} ({W}x{H}, {len(items)} tiles)")
