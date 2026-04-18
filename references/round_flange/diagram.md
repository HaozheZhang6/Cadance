# DIN 2573 / EN 1092-1 Round Flange — Parameter Diagram

```
Top view:
              D (outer diameter)
        ←————————————————→
       /                   \
      |  ○  ○  bolt holes  ○|
      |    ←— K (bolt PCD)  |
      |         ○           |
      |       ╔═══╗         |  ← inner bore (DN)
      |       ║   ║         |
      |       ╚═══╝         |
      |  ○              ○   |
       \       ○           /
        \________________/

Side view:
   ┌───────────────────────┐
   │                       │  ↑ b (flange thickness)
   │    FLANGE BODY        │
   └──────┬─────────┬──────┘  ↓
          │  bore   │
          │  (DN)   │
```

## Parameters

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| `outer_radius` | D/2 | Outer radius of the circular flange disc (mm). D is the outer diameter per DIN 2573 table. |
| `inner_radius` | DN/2 | Bore radius (mm). Approximately equal to nominal pipe bore / 2. |
| `height` | b | Axial thickness of the flange disc (mm). Controls flange rigidity. |
| `bolt_circle_radius` | K/2 | Radius of the pitch circle on which bolt holes are located (mm). |
| `bolt_count` | n | Number of equally-spaced bolt holes. Standard values: 4, 8, 12, 16, 20, 24. |
| `bolt_hole_diameter` | d | Diameter of each bolt clearance hole (mm). = bolt nominal + 1 mm (e.g. M16 → 18 mm). |
| `chamfer_length` | — | 45° chamfer on bottom face outer edge (mm). Aesthetic/functional. |
| `raised_face_radius` | — | Radius of raised sealing face on top surface (mm). Typically 0.55–0.72 × outer_radius. |
| `raised_face_height` | — | Height of raised sealing face above main flange surface (mm). |
| `neck_radius` | — | Radius of cylindrical neck/hub below flange (hard variant). Connects flange to pipe. |
| `neck_height` | — | Axial height of the neck/hub (mm). |
