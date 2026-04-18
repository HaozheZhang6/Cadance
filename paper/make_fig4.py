"""Figure 4: cases. GT | GEN.
Loads pre-rendered PNGs from docs/render_assets/png/.
"""
import os
import numpy as np
from PIL import Image
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

PNG_DIR = '/workspace/docs/render_assets/png'

# Each case: (col_label, gt_file, gen_file)
# gt/gen filenames relative to PNG_DIR
CASES = [
    ('c_a', 'fig4_38276_c9ef069a_0006_gt.png', 'fig4_38276_c9ef069a_0006_gen.png'),
    ('c_b', 'fig4_30708_4282508b_0000_gt.png',  'fig4_30708_4282508b_0000_gen.png'),
    ('c_c', 'fig4_118700_df55782f_0000_gt.png', 'fig4_118700_df55782f_0000_gen.png'),
    ('c_d', 'fig4_123331_28a27457_0000_gt.png',  'fig4_123331_28a27457_0000_gen.png'),
    ('c_e', 'fig4_136128_831e37a6_0000_gt.png', 'fig4_136128_831e37a6_0000_gen.png'),
    ('c_f', 'tbracket.png',  'tbracket.png'),
]

ROW_LABELS       = ['GT', 'Re-Act']
ROW_LABEL_COLORS = ['#2c3e50', '#2c3e50']

ncols = len(CASES)
nrows = 2

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

for ci, (lbl, gt_f, gen_f) in enumerate(CASES):
    for ri, fname in enumerate([gt_f, gen_f]):
        ax = fig.add_subplot(gs[ri, ci])
        ax.set_facecolor('white')
        ax.axis('off')
        img = load_png(fname)
        ax.imshow(img, aspect='equal')

plt.savefig('paper/fig4_final.png', dpi=180, bbox_inches='tight', facecolor='white')
print("Saved paper/fig4_final.png")
