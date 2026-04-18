# Render View Angle

- Elevation: 28°
- Azimuth: −42°
- Projection: perspective
- Camera zoom: 1.2×（object 占画面 ~80%）

对应的旋转矩阵：先绕 Z 轴转 −42°，再绕 X 轴转 28°（相机坐标系）。

---

## Rendered Gallery (512×512, elev=28°, azim=−42°)

### Brackets

| cbracket | tbracket |
|---|---|
| ![](png/cbracket.png) | ![](png/tbracket.png) |

### Fig 3

| gt | fix | bad |
|---|---|---|
| ![](png/fig3_gt.png) | ![](png/fig3_fix.png) | ![](png/fig3_bad.png) |

### Fig 5

| a | c | f |
|---|---|---|
| ![](png/fig5_a.png) | ![](png/fig5_c.png) | ![](png/fig5_f.png) |

### Complex

| 103481 | 109232 | 25199b | 25199c | 25199d |
|---|---|---|---|---|
| ![](png/complex_103481.png) | ![](png/complex_109232.png) | ![](png/complex_25199b.png) | ![](png/complex_25199c.png) | ![](png/complex_25199d.png) |

### Synth

| chamfer0 | fillet0 | revolve0 | revolve1 | shell0 | shell1 |
|---|---|---|---|---|---|
| ![](png/synth_chamfer0.png) | ![](png/synth_fillet0.png) | ![](png/synth_revolve0.png) | ![](png/synth_revolve1.png) | ![](png/synth_shell0.png) | ![](png/synth_shell1.png) |
