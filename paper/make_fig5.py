"""Figure 5: Repair cases. GT | Re-Act | CADLoop.
Loads pre-rendered PNGs from docs/render_assets/png/.
"""
import os
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

PNG_DIR = '/workspace/docs/render_assets/png'

# Each case: (col_label, gt_file, bad_file, fix_file)
# gt/bad/fix filenames relative to PNG_DIR
CASES = [
    ('c_a', 'fig5_a.png',          'fig5_a_bad.png',          'fig5_a_fix.png'),
    ('c_b', 'fig5_111387_gt.png',   'fig5_111387_bad.png',     'fig5_111387_fix.png'),
    ('c_c', 'fig5_41896_gt.png',    'fig5_41896_bad.png',      'fig5_41896_fix.png'),
    ('c_d', 'fig5_21734_gt.png',    'fig5_21734_bad.png',      'fig5_21734_fix.png'),
    ('c_e', 'fig5_142680_gt.png',   'fig5_142680_bad.png',     'fig5_142680_fix.png'),
    ('c_f', 'fig5_121469_gt.png',    'fig5_121469_bad.png',      'fig5_121469_fix.png'),
]

ROW_LABELS       = ['GT', 'Re-Act', 'CADLoop']
ROW_LABEL_COLORS = ['#2c3e50', '#2c3e50', '#2c3e50']

ncols = len(CASES)
nrows = 3

fig = plt.figure(figsize=(ncols * 2.6, nrows * 2.7 + 1.0))
fig.patch.set_facecolor('white')
gs = fig.add_gridspec(nrows, ncols, hspace=0.10, wspace=0.04,
                      left=0.09, right=0.99, top=0.91, bottom=0.05)

# Column labels
for ci, (lbl, *_) in enumerate(CASES):
    cx = 0.09 + (ci + 0.5) * (0.90 / ncols)
    fig.text(cx, 0.935, lbl, ha='center', va='bottom', fontsize=9,
             color='#2c3e50', style='italic')

# Row labels
for ri, (rl, rc) in enumerate(zip(ROW_LABELS, ROW_LABEL_COLORS)):
    ry = 0.91 - (ri + 0.5) * (0.86 / nrows)
    fig.text(0.005, ry, rl, ha='left', va='center', fontsize=11,
             fontweight='bold', color=rc, rotation=0)

def load_png(fname):
    path = os.path.join(PNG_DIR, fname)
    if os.path.exists(path):
        return np.array(Image.open(path).convert('RGB'))
    # placeholder white image if missing
    return np.full((320, 320, 3), 255, dtype=np.uint8)

for ci, (lbl, gt_f, bad_f, fix_f) in enumerate(CASES):
    for ri, fname in enumerate([gt_f, bad_f, fix_f]):
        ax = fig.add_subplot(gs[ri, ci])
        ax.set_facecolor('white')
        ax.axis('off')
        img = load_png(fname)
        ax.imshow(img, aspect='equal')

plt.savefig('paper/fig5_final.png', dpi=180, bbox_inches='tight', facecolor='white')
print("Saved paper/fig5_final.png")
