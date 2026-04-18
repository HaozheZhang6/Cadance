"""Figure 1: Teaser - From Complex CAD Generation to Verifiable Data Generation"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

fig, axes = plt.subplots(1, 3, figsize=(13, 5.5))
fig.patch.set_facecolor('white')

# Color palette
RED = '#e74c3c'
GREEN = '#27ae60'
BLUE = '#2980b9'
ORANGE = '#f39c12'
GRAY = '#95a5a6'
LIGHT_GRAY = '#ecf0f1'
DARK = '#2c3e50'
LIGHT_BLUE = '#d6eaf8'
LIGHT_RED = '#fadbd8'
LIGHT_GREEN = '#d5f5e3'

# === LEFT PANEL: Complex CAD Generation is Hard ===
ax = axes[0]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_facecolor('white')

# Title
ax.text(5, 9.5, 'Problem', fontsize=13, fontweight='bold', ha='center', color=DARK)
ax.text(5, 8.9, 'Complex CAD Generation', fontsize=10, ha='center', color=DARK)

# Construction chain boxes
steps = [
    ('Sketch 1\n(XY plane)', 0.8, 7.5),
    ('Extrude 1\n(+12mm)', 0.8, 6.1),
    ('Sketch 2\n(XZ plane)', 0.8, 4.7),
    ('Extrude 2\n(join)', 0.8, 3.3),
    ('Fillet r=2', 0.8, 1.9),
]
for label, x, y in steps:
    box = FancyBboxPatch((x, y-0.45), 3.5, 0.9, 
                          boxstyle="round,pad=0.1", 
                          facecolor=LIGHT_BLUE, edgecolor=BLUE, linewidth=1.2)
    ax.add_patch(box)
    ax.text(x+1.75, y, label, ha='center', va='center', fontsize=8, color=DARK)

# Arrows between steps
for i in range(len(steps)-1):
    ax.annotate('', xy=(2.55, steps[i+1][2]+0.45), xytext=(2.55, steps[i][2]-0.45),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.5))

# Error annotation
err_box = FancyBboxPatch((5.2, 4.2), 3.8, 1.5,
                          boxstyle="round,pad=0.15",
                          facecolor=LIGHT_RED, edgecolor=RED, linewidth=1.5)
ax.add_patch(err_box)
ax.text(7.1, 5.05, '✗ Sign flip in\nXZ coords', ha='center', va='center', fontsize=8, color=RED, fontweight='bold')

# Arrow from chain to error
ax.annotate('', xy=(5.2, 4.95), xytext=(4.3, 4.7),
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.5))

# Problem labels
for txt, y in [('Long-horizon chain', 1.2), ('Local error propagates', 0.7), ('No validation signal', 0.2)]:
    ax.text(5.0, y, '⚠  '+txt, fontsize=7.5, color=GRAY, ha='center')

# === CENTER PANEL: Our Key Idea ===
ax = axes[1]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_facecolor(LIGHT_GRAY)

ax.text(5, 9.5, 'Key Idea', fontsize=13, fontweight='bold', ha='center', color=DARK)
ax.text(5, 8.9, 'Verifiable Program Synthesis', fontsize=10, ha='center', color=DARK)

# LLM box
llm_box = FancyBboxPatch((2.5, 6.8), 5, 1.4,
                          boxstyle="round,pad=0.15",
                          facecolor='#f8c471', edgecolor=ORANGE, linewidth=1.8)
ax.add_patch(llm_box)
ax.text(5, 7.5, '🤖  LLM\n(CadQuery Generator)', ha='center', va='center', fontsize=9, color=DARK, fontweight='bold')

ax.annotate('', xy=(5, 6.8), xytext=(5, 6.1),
            arrowprops=dict(arrowstyle='->', color=DARK, lw=2))

# Code snippet box
code_box = FancyBboxPatch((0.5, 2.7), 9, 3.1,
                          boxstyle="round,pad=0.2",
                          facecolor='#1e1e1e', edgecolor='#444', linewidth=1.5)
ax.add_patch(code_box)

# Code text (monospace style)
code_lines = [
    ("import cadquery as cq", '#9cdcfe'),
    ("r = cq.Workplane('XY')", '#dcdcaa'),
    ("  .sketch().push(pts)", '#4ec9b0'),
    ("  .regularPolygon(r=15, n=6)", '#4ec9b0'),
    ("  .finalize().extrude(20)", '#4ec9b0'),
    ("result.val().exportStep('out.step')", '#ce9178'),
]
for i, (line, color) in enumerate(code_lines):
    ax.text(1.0, 5.5 - i*0.47, line, fontsize=7, color=color, fontfamily='monospace', va='center')

ax.annotate('', xy=(5, 2.7), xytext=(5, 2.1),
            arrowprops=dict(arrowstyle='->', color=DARK, lw=2))

ax.text(5, 1.7, '▶  Execute: subprocess + OCCT', ha='center', fontsize=8.5, color=DARK, style='italic')
ax.text(5, 1.1, '→ deterministic STEP output', ha='center', fontsize=8.5, color=DARK, style='italic')
ax.text(5, 0.4, 'Executable code = verifiable output', ha='center', fontsize=8.5, color=DARK, fontweight='bold')

# === RIGHT PANEL: Result ===
ax = axes[2]
ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.axis('off')
ax.set_facecolor('white')

ax.text(5, 9.5, 'Result', fontsize=13, fontweight='bold', ha='center', color=DARK)
ax.text(5, 8.9, 'Verified Program–Geometry Pairs', fontsize=10, ha='center', color=DARK)

# Verification steps
verify_steps = [
    ('Execute Program', BLUE, LIGHT_BLUE, '▶'),
    ('3D IoU ≥ 0.99\n(OCCT boolean)', GREEN, LIGHT_GREEN, '✓'),
    ('Visual 4-view\nrender check', BLUE, LIGHT_BLUE, '👁'),
    ('Metadata\nvalidation', BLUE, LIGHT_BLUE, '📋'),
]
for i, (label, ec, fc, icon) in enumerate(verify_steps):
    y = 7.8 - i*1.4
    box = FancyBboxPatch((1, y-0.45), 8, 0.9,
                          boxstyle="round,pad=0.1",
                          facecolor=fc, edgecolor=ec, linewidth=1.5)
    ax.add_patch(box)
    ax.text(2.0, y, icon, ha='center', va='center', fontsize=11)
    ax.text(5.5, y, label, ha='center', va='center', fontsize=8.5, color=DARK)
    if i < len(verify_steps)-1:
        ax.annotate('', xy=(5, y-0.45), xytext=(5, y-0.95),
                    arrowprops=dict(arrowstyle='->', color=DARK, lw=1.5))

# Result box
result_box = FancyBboxPatch((0.5, 1.0), 9, 1.8,
                             boxstyle="round,pad=0.15",
                             facecolor=LIGHT_GREEN, edgecolor=GREEN, linewidth=2.5)
ax.add_patch(result_box)
ax.text(5, 2.3, '✅  VERIFIED PAIR', ha='center', va='center', 
        fontsize=11, fontweight='bold', color=GREEN)
ax.text(5, 1.7, '1,784 pairs  ·  IoU mean 0.9999', ha='center', va='center', 
        fontsize=8.5, color=DARK)
ax.text(5, 1.2, 'Training-ready supervision', ha='center', va='center', 
        fontsize=8.5, color=DARK, style='italic')

ax.annotate('', xy=(5, 1.0), xytext=(5, 2.4),
            arrowprops=dict(arrowstyle='-', color=GREEN, lw=0))

# Arrow from 3rd verify step to result
ax.annotate('', xy=(5, 2.8), xytext=(5, 2.3),
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=2))

# Dividers between panels
for ax_idx in range(2):
    pass  # matplotlib handles this

# Overall title / headline
fig.text(0.5, 0.01, 
         'Complex Generation  →  Verifiable Program Synthesis  →  Verified Data', 
         ha='center', fontsize=11, fontweight='bold', color=DARK,
         style='italic')

plt.tight_layout(rect=[0, 0.05, 1, 1])
plt.savefig('/tmp/fig1_teaser.png', dpi=150, bbox_inches='tight', facecolor='white')
print("Saved /tmp/fig1_teaser.png")
