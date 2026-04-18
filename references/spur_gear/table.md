# ISO 54 / DIN 780 Standard Gear Module Values

## Preferred Module Series

Source: https://roymech.co.uk/Useful_Tables/Drive/Gears.html (ISO 54 / DIN 780 values)
Cross-reference: KHK Gears technical reference https://www.khkgears.net/gear-knowledge/

| Series | Module values (mm) |
|--------|--------------------|
| **Series 1** (preferred) | 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 16, 20 |
| **Series 2** (secondary) | 1.125, 1.375, 1.75, 2.25, 2.75, 3.5, 4.5, 5.5, 7, 9, 11, 14, 18 |

**Note:** Use series 1 values whenever possible. Series 2 only when series 1 does not meet design constraints.

Extended range (ISO 54 includes):
- Below 1 mm: 0.1, 0.12, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8 (for watches, instruments)
- Above 20 mm: 25, 32, 40, 50 (heavy engineering)

## Gear Dimensional Table (derived from module m)

All formulas per ISO 54 / ISO 53. Pressure angle α = 20°.

| Module m | z=12 | z=17 | z=25 | z=40 | z=60 |
|----------|------|------|------|------|------|
| **PCD = m×z (mm)** | | | | | |
| 1        | 12   | 17   | 25   | 40   | 60   |
| 1.5      | 18   | 25.5 | 37.5 | 60   | 90   |
| 2        | 24   | 34   | 50   | 80   | 120  |
| 3        | 36   | 51   | 75   | 120  | 180  |
| 4        | 48   | 68   | 100  | 160  | 240  |
| 5        | 60   | 85   | 125  | 200  | 300  |
| 6        | 72   | 102  | 150  | 240  | 360  |
| 8        | 96   | 136  | 200  | 320  | 480  |
| 10       | 120  | 170  | 250  | 400  | 600  |

**Tip diameter** Da = m × (z + 2) — add 2×m to PCD
**Root diameter** Df = m × (z − 2.5) — subtract 2.5×m from PCD

## Tooth Count Ranges (typical for each difficulty)

Source: commercial gear catalogs (Boston Gear, KHK, SDP/SI)
Reference: https://www.sdp-si.com/resources/

| Application | z range | Notes |
|-------------|---------|-------|
| Minimum (no undercut) | 12–17 | Below 17 may need profile shift at α=20° |
| Small pinion | 12–20 | High speed driver |
| Medium gears | 20–50 | Most common |
| Large gears / ring gears | 50–200 | Slow speed, high torque |

**Undercut limit:** z_min = 2 / sin²(α) = 17.1 at α=20° (theoretical); profile-shifted gears can use z < 17.
