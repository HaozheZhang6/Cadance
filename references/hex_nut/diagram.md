# ISO 4032 Hex Nut — Parameter Diagram

```
   ←——— s ———→
  /‾‾‾‾‾‾‾‾‾\   ↑
 /           \   m (nut height)
|   ○ bore M  |
 \           /   ↓
  \_________/

Top view:          Side view:
   ___             _______
  /   \           |       |  ↑ m
 / hex \          |  HEX  |
 \     /          |_______|  ↓
  \___/
```

## Parameters

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| `nominal_size` | M | Thread nominal diameter = bore diameter (mm). |
| `across_flats` | s | Distance across two parallel faces of the hex body (mm). Wrench size. |
| `across_corners` | e | Diagonal across opposite corners = s / cos(30°) (mm). |
| `height` | m | Total nut height (mm). ~0.8 × M for small sizes. |
| `bore_diameter` | — | Inner bore = M (thread minor diameter approximated as M for geometry). |
| `chamfer` | — | Optional 45° chamfer on top and bottom face edges; typically 0.1–0.15 × m. |
