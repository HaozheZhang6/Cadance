# CadQuery Op Syntax Error Log

## 1. `cutBlind` always requires NEGATIVE depth — for BOTH `>Z` and `<Z` faces

**Rule:** `cutBlind(depth)` cuts in the POSITIVE local-Z direction of the workplane.
For both `>Z` and `<Z` faces: local +Z = outward normal → positive depth cuts INTO EMPTY SPACE, removes nothing.
Negative depth cuts AGAINST the outward normal = INTO the solid.

**This holds for both face directions:**
```
faces('>Z').cutBlind(+5)  → removed=0.0   ← no-cut (outward = empty space)
faces('>Z').cutBlind(-5)  → removed=565.5 ← CORRECT (inward = into solid)
faces('<Z').cutBlind(+5)  → removed=0.0   ← no-cut (outward = empty space below)
faces('<Z').cutBlind(-5)  → removed=565.5 ← CORRECT (inward = upward into solid)
```

**Both faces work equally.** Using `>Z` shows the groove on top; `<Z` shows it on the bottom.
For rim_heavy: medium randomly picks one face (`>Z` or `<Z`); hard cuts both faces symmetrically.

**In builder.py:** fixed by auto-negating: `wp.cutBlind(-abs(a["depth"]))`.
Family code passes positive `depth` values; builder always negates.

**Affected families (all used positive depth before fix):**
- `spur_gear.py`: web_recess (solid_disc, rim_heavy), rim_boss inner cut, bellows bolt holes
- `helical_gear.py`: web_recess
- `bevel_gear.py`: if any cutBlind used
- `bellows.py`: bolt hole cutBlind
- `impeller.py`: if any cutBlind used

**Discovery:** 2026-04-04 via user review of gid 18909/18916.
All synth_gears_kw_s1502 solid_disc medium/hard STEP files rebuilt after fix.

---

## 2. `transformed` offset in `union`/`cut` sub-programs

**Rule:** `union` and `cut` sub-programs start from a FRESH `cq.Workplane("XY")` at z=0 centered.
`cylinder(height, radius)` in a sub-program is CENTERED at z=0 → spans [-h/2, +h/2].

**To place cylinder at z=[a, b]:** use `transformed(offset=[0,0,(a+b)/2])` first, then `cylinder(b-a, r)`.

**Example (rim_heavy hub centered at gear mid-height):**
```python
Op("union", {"ops": [
    {"name": "transformed", "args": {"offset": [0, 0, fw/2], "rotate": [0,0,0]}},
    {"name": "cylinder", "args": {"height": fw, "radius": hub_r}},
]})
```

---

## 3. `polarArray` + `cutBlind` needs `circle()` in between

**Rule:** `hole(diameter)` implicitly creates a circular profile. `cutBlind` does NOT — it cuts
whatever pending wire is on the stack. After `polarArray`, there are only pending POINTS, not wires.

**Wrong:** `polarArray(...)` → `cutBlind(depth)`
**Correct:** `polarArray(...)` → `circle(r)` → `cutBlind(-depth)`

---

## 5. Annular (ring-shaped) cut requires TWO circles before `cutBlind`

**Rule:** `circle(r).cutBlind(d)` cuts a full disc of radius r. To cut only the annular region
between an inner and outer radius, push BOTH circles before cutBlind:

```python
.faces(">Z").workplane()
.circle(outer_r)   # outer boundary
.circle(inner_r)   # inner boundary (hole left intact)
.cutBlind(-depth)
```

CadQuery interprets nested wires as a profile with a hole — the annular region is cut, center is untouched.

**Wrong:** `circle(web_r).cutBlind(-d)` → cuts full disc (erases hub/bore area)
**Correct:** `circle(web_r).circle(hub_r).cutBlind(-d)` → cuts only the web zone

**Affected families fixed 2026-04-04:**
- `spur_gear.py`: rim_heavy web recess, solid_disc web recess
  - rim_heavy: removed redundant hub union; annular cut replaces it
  - solid_disc: inner radius = bore_diameter/2

**Reference:** `tmp/manual_family_previews/spurs_gear.py` line 9-11

---

## 4. `cylinder()` is always centered at workplane origin

**Rule:** `cq.Workplane.cylinder(height, radius)` places the cylinder CENTERED at the current
workplane origin, spanning [-height/2, +height/2] in local Z.

This differs from how one might expect "place cylinder starting at current plane".
Always account for this when positioning cylinders with `transformed` offsets.
