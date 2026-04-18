# ISO 4014 Hex Bolt — Parameter Diagram

```
   ←——— s ———→
  /‾‾‾‾‾‾‾‾‾\   ↑
 /     HEX   \   k (head height)
|_____________|  ↓
|             |  ↑
|   SHANK     |  shaft_length (L - k)
|  (unthread) |
|_ _ _ _ _ _ _|  ← thread starts here
| ~ ~ ~ ~ ~ ~ |  ↑
| ~ THREAD ~  |  b (thread length)
| ~ ~ ~ ~ ~ ~ |  ↓
              ↓

      ←d→  (nominal diameter M)
```

## Parameters

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| `nominal_size` | M | Thread nominal diameter (mm). Also shaft diameter. |
| `across_flats` | s | Distance between two parallel flats of the hexagonal head (mm). Wrench size. |
| `across_corners` | e | Distance between opposite corners of hex head = s / cos(30°) (mm). |
| `head_height` | k | Height of the hexagonal head measured from underside to top (mm). |
| `shaft_length` | L | Total bolt length from underside of head to tip (mm). From ISO 888 preferred series. |
| `thread_length` | b | Length of threaded portion at tip of shank (mm). Depends on L and M per ISO 4014 Table 1. |
| `thread_pitch` | p | Distance between adjacent thread crests (mm). Coarse thread per ISO 261. |
| `chamfer` | — | Optional 45° chamfer on top edge of head; typically 0.1–0.15 × k. |
