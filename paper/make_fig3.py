"""Figure 3: Skill-Based Modular System vs. Rigid Workflow"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.patches as mpatches

fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(13, 6.5))
fig.patch.set_facecolor('white')

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
GRAY = '#95a5a6'
LIGHT_GRAY = '#ecf0f1'

def rbox(ax, x, y, w, h, label, sub='', fc=LIGHT_BLUE, ec=BLUE, fontsize=9, bold=False):
    b = FancyBboxPatch((x-w/2, y-h/2), w, h,
                        boxstyle="round,pad=0.1",
                        facecolor=fc, edgecolor=ec, linewidth=1.8, zorder=3)
    ax.add_patch(b)
    fw = 'bold' if bold else 'normal'
    ax.text(x, y+(0.12 if sub else 0), label, ha='center', va='center',
            fontsize=fontsize, fontweight=fw, color=DARK, zorder=4)
    if sub:
        ax.text(x, y-0.2, sub, ha='center', va='center', fontsize=7, color=GRAY, zorder=4)

def arr(ax, x1, y1, x2, y2, color=DARK, lw=2, style='->'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw), zorder=2)

# ══════════════════════════════════════════════════════════
# LEFT: Rigid Workflow
# ══════════════════════════════════════════════════════════
ax = ax_left
ax.set_xlim(0, 6)
ax.set_ylim(0, 7)
ax.axis('off')

ax.text(3, 6.6, 'Rigid Workflow', fontsize=13, fontweight='bold', ha='center', color=RED)
ax.text(3, 6.15, 'Monolithic sequential pipeline', fontsize=9, ha='center', color=GRAY, style='italic')

# Steps
rigid_steps = [
    (3, 5.4, 'Input', 'GT STEP + JSON', LIGHT_BLUE, BLUE),
    (3, 4.3, 'Generate', 'single provider, single attempt', LIGHT_ORANGE, ORANGE),
    (3, 3.2, 'Execute', 'fixed subprocess call', LIGHT_BLUE, BLUE),
    (3, 2.1, 'Validate', 'IoU check', LIGHT_BLUE, BLUE),
    (3, 1.0, 'Output', 'pass or discard', LIGHT_GRAY, GRAY),
]
for x, y, lbl, sub, fc, ec in rigid_steps:
    rbox(ax, x, y, 3.8, 0.75, lbl, sub, fc=fc, ec=ec)

for i in range(len(rigid_steps)-1):
    y1 = rigid_steps[i][1] - 0.375
    y2 = rigid_steps[i+1][1] + 0.375
    arr(ax, 3, y1, 3, y2, color=GRAY, lw=1.8)

# Failure → discard
fail_x = 5.0
fail_y = 2.1
ax.annotate('', xy=(fail_x, fail_y), xytext=(3+1.9, fail_y),
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.8), zorder=2)
rbox(ax, fail_x+0.4, fail_y, 0.9, 0.7, 'FAIL', 'discard', fc=LIGHT_RED, ec=RED, fontsize=8)
ax.text(4.5, fail_y+0.5, 'any failure\n→ hard stop', fontsize=7.5, color=RED, ha='center', style='italic')

# Problem labels (below)
problems = [
    (3, 0.5, RED, 'brittle: one failure breaks the chain'),
    (3, 0.17, RED, 'no recovery for hard cases'),
    (3, -0.16, RED, 'cannot route to different strategies'),
    (3, -0.49, RED, 'hard to extend or maintain'),
]
for x, y, c, t in problems:
    ax.text(x, y, '✗  '+t, ha='center', fontsize=7.5, color=c)

# ══════════════════════════════════════════════════════════
# RIGHT: Skill-Based Modular System
# ══════════════════════════════════════════════════════════
ax = ax_right
ax.set_xlim(0, 8)
ax.set_ylim(-0.6, 7)
ax.axis('off')

ax.text(4, 6.6, 'Skill-Based Modular System', fontsize=13, fontweight='bold', ha='center', color=GREEN)
ax.text(4, 6.15, 'Reusable, composable, independently upgradeable skills', fontsize=9, ha='center', color=GRAY, style='italic')

# Central hub
hub_x, hub_y = 4.0, 3.3
hub = FancyBboxPatch((hub_x-1.1, hub_y-0.55), 2.2, 1.1,
                      boxstyle="round,pad=0.15",
                      facecolor=LIGHT_GREEN, edgecolor=GREEN, linewidth=2.5, zorder=3)
ax.add_patch(hub)
ax.text(hub_x, hub_y+0.1, 'Verified Store', ha='center', va='center',
        fontsize=9.5, fontweight='bold', color=GREEN, zorder=4)
ax.text(hub_x, hub_y-0.2, '1,784 pairs · JSONL', ha='center', va='center',
        fontsize=7.5, color=GRAY, zorder=4)

# Skills around hub
skills = [
    # (x, y, name, sub, fc, ec)
    (1.1, 5.8, 'Generation\nSkill', 'LLM provider', LIGHT_ORANGE, ORANGE),
    (4.0, 5.8, 'Execution\nSkill', 'subprocess + OCCT', LIGHT_BLUE, BLUE),
    (6.9, 5.8, 'Verification\nSkill', 'IoU gate', LIGHT_BLUE, BLUE),
    (1.1, 0.9, 'Manual Check\nSkill', 'hard tail → human', LIGHT_GRAY, GRAY),
    (4.0, 0.9, 'Repair\nSkill', 'targeted heuristics', '#f5eef8', PURPLE),
    (6.9, 0.9, 'Assembly\nSkill', 'SFT JSONL', LIGHT_GREEN, GREEN),
]
skill_boxes = []
for x, y, lbl, sub, fc, ec in skills:
    rbox(ax, x, y, 2.0, 0.9, lbl, sub, fc=fc, ec=ec, fontsize=8.5)
    skill_boxes.append((x, y))

# Arrows hub ↔ skills
for x, y in skill_boxes:
    # From skill to hub (above) or hub to skill (below)
    if y > hub_y:
        ax.annotate('', xy=(hub_x + (x-hub_x)*0.45, hub_y+0.55-(hub_y+0.55-y)*0.15),
                    xytext=(x, y - 0.45),
                    arrowprops=dict(arrowstyle='<->', color='#7f8c8d', lw=1.5), zorder=2)
    else:
        ax.annotate('', xy=(hub_x + (x-hub_x)*0.45, hub_y-0.55+(y-hub_y+0.55)*0.15),
                    xytext=(x, y + 0.45),
                    arrowprops=dict(arrowstyle='<->', color='#7f8c8d', lw=1.5), zorder=2)

# Key advantage labels
advantages = [
    (0.3, -0.05, GREEN, '✓  Reusable: skills work across all part types'),
    (0.3, -0.3, GREEN, '✓  Extensible: swap or add skills without redesign'),
    (0.3, -0.55, GREEN, '✓  Robust: heterogeneous failures handled per-case'),
    (4.3, -0.05, GREEN, '✓  Hard-tail: manual check is first-class, not afterthought'),
    (4.3, -0.3, GREEN, '✓  Provenance: every pair has source, timestamp, IoU'),
    (4.3, -0.55, GREEN, '✓  Cheap: expensive resource only for hardest cases'),
]
for x, y, c, t in advantages:
    ax.text(x, y, t, fontsize=7.5, color=c, va='center')

# Divider between panels
fig.text(0.5, 0.5, 'vs', ha='center', va='center', fontsize=20, 
         fontweight='bold', color='#bdc3c7',
         transform=fig.transFigure)

# Title
fig.text(0.5, 0.97, 'Figure 3.  Why Skill-Based Composition Instead of a Rigid Workflow',
         ha='center', fontsize=12, fontweight='bold', color=DARK)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('/tmp/fig3_skills.png', dpi=150, bbox_inches='tight', facecolor='white')
print("Saved /tmp/fig3_skills.png")
