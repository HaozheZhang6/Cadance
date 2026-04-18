"""Figure 2: Verification-Guided CAD Data Curation Pipeline"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(figsize=(14, 6))
fig.patch.set_facecolor('white')
ax.set_xlim(0, 14)
ax.set_ylim(0, 6)
ax.axis('off')

BLUE = '#2980b9'
GREEN = '#27ae60'
RED = '#e74c3c'
ORANGE = '#f39c12'
PURPLE = '#8e44ad'
DARK = '#2c3e50'
LIGHT_BLUE = '#d6eaf8'
LIGHT_GREEN = '#d5f5e3'
LIGHT_RED = '#fadbd8'
LIGHT_ORANGE = '#fef9e7'
LIGHT_PURPLE = '#f5eef8'
GRAY = '#7f8c8d'
LIGHT_GRAY = '#ecf0f1'

def box(ax, x, y, w, h, label, sublabel='', fc=LIGHT_BLUE, ec=BLUE, fontsize=9):
    b = FancyBboxPatch((x-w/2, y-h/2), w, h,
                        boxstyle="round,pad=0.08",
                        facecolor=fc, edgecolor=ec, linewidth=1.8, zorder=3)
    ax.add_patch(b)
    ax.text(x, y + (0.15 if sublabel else 0), label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color=DARK, zorder=4)
    if sublabel:
        ax.text(x, y-0.22, sublabel, ha='center', va='center', fontsize=7, color=GRAY, zorder=4)

def arrow(ax, x1, y1, x2, y2, color=DARK, label='', lw=2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw),
                zorder=2)
    if label:
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx+0.1, my+0.15, label, ha='left', fontsize=7.5, color=color, style='italic', zorder=5)

# ── MAIN FLOW (top row, y=4.2) ──────────────────────────────────────────────
main_y = 4.2
nodes = [
    (1.1, main_y, 'Input', 'GT STEP + JSON', LIGHT_BLUE, BLUE),
    (3.2, main_y, 'Generation\nSkill', 'LLM (CadQuery)', LIGHT_ORANGE, ORANGE),
    (5.4, main_y, 'Execution\nSkill', 'subprocess + OCCT', LIGHT_BLUE, BLUE),
    (7.7, main_y, 'Verification\nSkill', 'IoU = V_intersect/V_union', LIGHT_BLUE, BLUE),
    (10.1, main_y, 'Decision', 'IoU ≥ 0.99?', LIGHT_GREEN, GREEN),
    (12.5, main_y, 'Verified\nStore', '1,784 pairs', LIGHT_GREEN, GREEN),
]
for x, y, lbl, sub, fc, ec in nodes:
    box(ax, x, y, 1.8, 0.95, lbl, sub, fc=fc, ec=ec, fontsize=8.5)

# Arrows main flow
arrow(ax, 2.0, main_y, 2.3, main_y)
arrow(ax, 4.1, main_y, 4.5, main_y)
arrow(ax, 6.3, main_y, 6.8, main_y)
arrow(ax, 8.6, main_y, 9.2, main_y)
arrow(ax, 11.0, main_y, 11.6, main_y, color=GREEN, label='PASS')

# ── FAILURE PATHS ───────────────────────────────────────────────────────────

# 1. Execution failure → cascade to next provider
# From Execution down, back to Generation
arrow(ax, 5.4, main_y-0.47, 5.4, 2.65, color=RED)
ax.text(5.6, 3.4, 'Exec fail', fontsize=7.5, color=RED, style='italic')

# Cascade box (below)
cascade_y = 2.2
box(ax, 3.8, cascade_y, 2.5, 0.85, 'Provider\nCascade', 
    'codex → openai → glm', fc='#fdebd0', ec=ORANGE, fontsize=8)
ax.annotate('', xy=(3.8, cascade_y+0.42), xytext=(5.4, 2.65),
            arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.8), zorder=2)
ax.annotate('', xy=(3.2, main_y-0.47), xytext=(3.2, cascade_y+0.42),
            arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.8), zorder=2)
ax.text(2.9, 3.1, 'retry', fontsize=7.5, color=ORANGE, style='italic')

# 2. FAIL (IoU < 0.97) → discard
arrow(ax, 10.1, main_y-0.47, 10.1, 2.65, color=RED)
discard_y = 2.2
box(ax, 10.1, discard_y, 1.7, 0.75, 'Discard', 'IoU < 0.97', fc=LIGHT_RED, ec=RED, fontsize=8)
ax.text(10.3, 3.1, 'FAIL', fontsize=7.5, color=RED, style='italic')

# 3. Near-miss (0.97 ≤ IoU < 0.99) → Repair → back to Verify
nearmiss_y = 2.2
box(ax, 7.7, nearmiss_y, 1.8, 0.75, 'Repair\nSkill', 'near-miss queue', fc='#f5eef8', ec=PURPLE, fontsize=8)
ax.annotate('', xy=(7.7, nearmiss_y+0.375), xytext=(7.7, main_y-0.47),
            arrowprops=dict(arrowstyle='->', color=PURPLE, lw=1.8), zorder=2)
ax.text(7.9, 3.1, '0.97≤IoU<0.99', fontsize=7, color=PURPLE, style='italic')

# Manual check sub-path
box(ax, 7.7, 0.9, 1.8, 0.75, 'Manual\nCheck', 'hard tail', fc='#fdfefe', ec=GRAY, fontsize=8)
ax.annotate('', xy=(7.7, 1.27), xytext=(7.7, nearmiss_y-0.375),
            arrowprops=dict(arrowstyle='->', color=GRAY, lw=1.5), zorder=2)
# Back to verifier from manual check
ax.annotate('', xy=(8.6, main_y-0.47), xytext=(8.6, 1.6),
            arrowprops=dict(arrowstyle='->', color=PURPLE, lw=1.8), zorder=2)
ax.plot([7.7+0.9, 8.6], [0.9, 0.9], color=PURPLE, lw=1.5)
ax.plot([8.6, 8.6], [0.9, 1.6], color=PURPLE, lw=1.5)
ax.text(9.0, 1.3, 'fixed →\nre-verify', fontsize=7, color=PURPLE, style='italic')

# ── Record schema box ────────────────────────────────────────────────────────
schema_y = 4.2
box(ax, 12.5, 2.2, 1.7, 0.8, 'Record\nSchema', 'JSONL + provenance', fc=LIGHT_GREEN, ec=GREEN, fontsize=8)
ax.annotate('', xy=(12.5, 2.6), xytext=(12.5, main_y-0.47),
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=1.5), zorder=2)

# ── Title ────────────────────────────────────────────────────────────────────
ax.text(7.0, 5.65, 'Figure 2. Verification-Guided CAD Data Curation Pipeline', 
        ha='center', fontsize=12, fontweight='bold', color=DARK)
ax.text(7.0, 5.2, 
        'Main flow (→): generate program → execute → verify IoU → accept.  '
        'Failure paths (↓): cascade providers, route near-misses to repair, escalate hardest to manual check.',
        ha='center', fontsize=8, color=GRAY, style='italic')

plt.tight_layout()
plt.savefig('/tmp/fig2_pipeline.png', dpi=150, bbox_inches='tight', facecolor='white')
print("Saved /tmp/fig2_pipeline.png")
