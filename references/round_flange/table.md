# DIN 2573 / EN 1092-1 PN6 Slip-On Flange Dimensions

Source: DIN 2573:1998 standard values, as published in German engineering handbooks
and reproduced by manufacturer catalogs (Klann, RFF, Haas GmbH).
Cross-reference: https://www.fasteners.eu/standards/DIN/2573/

All dimensions in mm.
`DN` = nominal bore; `D` = flange outer diameter; `b` = flange thickness;
`K` = bolt circle diameter; `n` = number of bolt holes; `d` = bolt hole diameter.

| DN  | D   | b  | K   | n  | d    | Bolt size |
|-----|-----|----|-----|----|------|-----------|
| 10  |  75 | 12 |  50 |  4 | 11   | M10       |
| 15  |  80 | 12 |  55 |  4 | 11   | M10       |
| 20  |  90 | 14 |  65 |  4 | 11   | M10       |
| 25  | 100 | 14 |  75 |  4 | 11   | M10       |
| 32  | 120 | 14 |  90 |  4 | 14   | M12       |
| 40  | 130 | 14 | 100 |  4 | 14   | M12       |
| 50  | 140 | 14 | 110 |  4 | 14   | M12       |
| 65  | 160 | 14 | 130 |  4 | 14   | M12       |
| 80  | 190 | 16 | 150 |  4 | 18   | M16       |
| 100 | 210 | 16 | 170 |  4 | 18   | M16       |
| 125 | 240 | 18 | 200 |  8 | 18   | M16       |
| 150 | 265 | 18 | 225 |  8 | 18   | M16       |
| 200 | 320 | 20 | 280 |  8 | 18   | M16       |
| 250 | 375 | 22 | 335 | 12 | 18   | M16       |
| 300 | 440 | 22 | 395 | 12 | 22   | M20       |
| 350 | 490 | 22 | 445 | 12 | 22   | M20       |
| 400 | 540 | 24 | 495 | 16 | 22   | M20       |
| 450 | 595 | 24 | 550 | 16 | 22   | M20       |
| 500 | 645 | 24 | 600 | 20 | 22   | M20       |
| 600 | 755 | 24 | 705 | 20 | 26   | M24       |

**Notes:**
1. DN = nominal bore size. Actual bore depends on pipe schedule. For PN6, inner diameter ≈ DN + wall clearance.
2. Bolt holes are `d = bolt_size + 1 mm` clearance (e.g. M16 bolt → d=18 mm hole).
3. Flange outer radius = D/2; bolt circle radius = K/2.
4. The codebase `round_flange` samples outer_radius 20–100 mm, which corresponds to DN10–DN100 flanges (D/2 = 37.5–105 mm).

## Derived CAD Parameters Mapping

| DIN 2573 symbol | CAD `sample_params` key | Notes |
|-----------------|------------------------|-------|
| D/2 | `outer_radius` | Flange outer radius |
| DN/2 approx | `inner_radius` | Bore radius; actual = pipe OD/2 |
| b | `height` | Flange face-to-face thickness |
| K/2 | `bolt_circle_radius` | Radius of bolt hole circle |
| n | `bolt_count` | Number of bolt holes |
| d | `bolt_hole_diameter` | Clearance hole diameter |
