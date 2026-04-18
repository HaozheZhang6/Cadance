"""Ground truth CadQuery code for L2_05: Hollow Box (Shelled).

This creates an 80x60x50mm box, shelled with 3mm walls, top open.

Design decisions:
- Create solid box first
- Select top face with faces(">Z")
- shell() with negative value shells inward
- Selected face is removed (becomes the opening)

Volume calculation:
- Outer box: 80 * 60 * 50 = 240,000 mm³
- Inner cavity: (80-6) * (60-6) * (50-3) = 74 * 54 * 47 = 187,812 mm³
  (subtract 2*3=6 from width/depth for both walls, only 3 from height for bottom)
- Wall volume: 240,000 - 187,812 = 52,188 mm³
- Wait, that's wrong. Let me recalculate:
  Inner after shell: walls are 3mm thick
  Inner dimensions: (80-6) x (60-6) x (50-3) = 74 x 54 x 47
  But top is open, so inner height goes full 50-3=47mm from bottom

Actually for a shell:
- Outer: 80 x 60 x 50
- Inner (subtractive): 74 x 54 x 47 = 187,812
- Shell removes the inner: 240,000 - 187,812 = 52,188 mm³
- But the top face (opening) also removes material... Let me reconsider.

For shell(-3) on box with top open:
- Start with solid 80x60x50
- Remove interior cavity leaving 3mm walls on 5 sides (bottom + 4 walls)
- Inner cavity: 74 x 54 x (50-3) = 74 x 54 x 47

Hmm, CadQuery shell behavior: shell(-3) makes walls 3mm thick by hollowing inward.
Volume = outer - inner = 240,000 - (74 * 54 * 47) = 240,000 - 187,812 = 52,188

Let me verify with different approach:
- Bottom: 80*60*3 = 14,400
- Front wall: 80*47*3 = 11,280
- Back wall: 80*47*3 = 11,280
- Left wall: 54*47*3 = 7,614
- Right wall: 54*47*3 = 7,614
- Total walls: 14,400 + 11,280 + 11,280 + 7,614 + 7,614 = 52,188 ✓

Hmm but I counted wrong - the side walls don't go full depth because corners overlap.

Let me think again:
- Bottom slab: 80 * 60 * 3 = 14,400
- Four walls around the edge, inside the footprint minus bottom:
  - Front/Back: 80 * (50-3) * 3 = 80 * 47 * 3 = 11,280 each
  - Left/Right: (60 - 2*3) * (50-3) * 3 = 54 * 47 * 3 = 7,614 each
  - Total walls: 2*11,280 + 2*7,614 = 37,788
- Bottom: 14,400
- Total: 14,400 + 37,788 = 52,188

Hmm let me reconsider - CadQuery shell works differently. I'll use the subtraction approach:
Outer solid - Inner void = shell volume
80*60*50 - 74*54*47 = 240,000 - 187,812 = 52,188 mm³

Actually, I realize my wall calculation is double-counting corners. Let me just trust the subtraction:
Volume = 240,000 - 187,812 = 52,188 mm³

Wait, the inner dimensions should be 74x54x47 if walls are 3mm on sides and bottom.
But I want to double-check the inner height. If the box is 50mm tall, and we shell with 3mm walls,
and the TOP is OPEN (removed), then:
- Bottom wall: 3mm thick
- Inner height: 50 - 3 = 47mm (from inner bottom to top opening)

So inner cavity is 74 x 54 x 47 = 187,812
Shell volume = 240,000 - 187,812 = 52,188

Hmm, but I put 50328 in the spec. Let me recalculate...
74 * 54 = 3996
3996 * 47 = 187,812
240,000 - 187,812 = 52,188

I had an error in my spec. Let me correct it to 52188.
"""

import cadquery as cq

# Create hollow box with 3mm walls, top open
result = (
    cq.Workplane("XY")
    .box(80, 60, 50)
    .faces(">Z")  # Select top face (will be removed)
    .shell(-3)  # Shell inward with 3mm wall thickness
)

# Expected properties:
# - Volume: 240,000 - 187,812 = 52,188 mm³
# - Bounding box: 80 x 60 x 50 (outer dimensions unchanged)
# - Faces: 10 (5 outer + 5 inner walls/bottom, top is open)
# - Edges: 24 (12 outer + 12 inner at opening rim)
