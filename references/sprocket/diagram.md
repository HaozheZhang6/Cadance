# DIN 8187 / ISO 606 Sprocket — Parameter Diagram

```
        Da (tip diameter)
       ←————————→
      /‾‾‾‾‾‾‾‾‾‾\
    /   tooth tips   \     ↑ disc_thickness (t)
   | ↑PCD            |     ↓
   |                 |
    \   root circle  /
      \____________/
       ←——Df——→  (root diameter)
         ○  ← bore_diameter

Side view with hub:
  _______________
 |               |
 |   SPROCKET    |  ↑ disc_thickness
 |_______   _____|  ↓
         | |
         | |  ↑ hub_height
         |_|  ↓
      ←hub_d→
        ○ bore
```

## Parameters

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| `pitch` | p | Chain pitch: center-to-center distance between chain roller pins (mm). From ISO 606 standard series. |
| `roller_diameter` | dr | Outer diameter of the chain roller (mm). Determines tooth root shape. |
| `n_teeth` | z | Number of sprocket teeth. Minimum 9 to avoid excessive polygon effect. |
| `pitch_circle_diameter` | PCD | Diameter of circle passing through roller centers when engaged: p / sin(π/z) (mm). |
| `tip_diameter` | Da | Outer diameter of tooth tips: PCD + 0.8 × dr (mm). |
| `root_diameter` | Df | Diameter at bottom of tooth gaps: PCD − dr (mm). Must exceed bore. |
| `disc_thickness` | t | Axial thickness of the toothed disc (mm). Typically 0.6–1.4 × dr. |
| `bore_diameter` | d_bore | Inner bore hole diameter (mm). Must be < Df × 0.5. |
| `hub_diameter` | d_hub | Outer diameter of cylindrical boss behind disc (mm). Present on medium/hard variants. |
| `hub_height` | h_hub | Axial height of hub boss behind disc (mm). |
| `keyway_width` | kw | Width of keyway slot in bore (mm). DIN 6885 proportions: ≈ 0.25 × bore. |
| `keyway_depth` | kd | Depth of keyway slot (mm). ≈ 0.12 × bore. |
