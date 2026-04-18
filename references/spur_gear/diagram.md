# ISO 54 Spur Gear — Parameter Diagram

```
           Da (tip/addendum circle)
          ←————————————→
         /‾‾‾‾‾‾‾‾‾‾‾‾‾‾\
        /   tooth tip      \
       | ↑ PCD = m×z       |    ↑
       |   (pitch circle)  |    face_width (b_f)
       |   root circle Df  |    ↓
        \                 /
         \_______________/
              ○  bore

Cross-section of one tooth:
   ___
  /   \   ← addendum (tip) = m above pitch line
─/─────\─  pitch line (r_p)
/  inv   \
\  olu   /  tooth flank
 \  te  /
  \____/  ← dedendum = 1.25×m below pitch line (root)
```

## Parameters

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| `module` | m | Fundamental size parameter (mm). Pitch = π×m. Tooth height ≈ 2.25×m. |
| `n_teeth` | z | Number of teeth. Must be ≥ 12 to avoid severe undercut at 20° pressure angle. |
| `pressure_angle` | α | Angle between tooth normal and pitch circle tangent. Standard = 20° (ISO 53). |
| `pitch_radius` | r_p | = m × z / 2 (mm). The reference circle radius. |
| `base_radius` | r_b | = r_p × cos(α). Involute unrolls from this circle. |
| `tip_radius` | r_a | = r_p + m. Outermost tooth radius. |
| `root_radius` | r_d | = r_p − 1.25 × m. Bottom of tooth gap. |
| `face_width` | b_f | Axial width of gear body (mm). Typical: 8m – 16m. |
| `bore_diameter` | d_bore | Central bore (mm). Must leave sufficient web material. |
| `hub_diameter` | d_hub | Boss diameter for spoked/rim variants (mm). |
| `n_spokes` | — | Number of spokes in spoked variant. Typical: 4–6. |
