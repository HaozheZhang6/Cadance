
## 2026-04-18 (session 2)

- UA-6 完成：所有 Tier 2 families 补全 ISO/DIN 表格驱动
  - bevel_gear: ISO 54 module + `rng.integers` for tooth count + DIN 6885A keyway
  - sprocket: DIN 6885A keyway (replaced proportional formula)
  - pulley: ISO 22 groove angles + ISO 4183 belt section table (done in session 1)
  - rect_frame: corrected standard N/A (EN 10219 doesn't apply); preferred-size table added
- Added `din6885a_keyway()` helper to `base.py` (shared DIN 6885A lookup)
- Bug Fix: spur_gear/helical_gear web recess + rim_boss verified (100% build pass)
- Preflight: propeller/manifold_block/lathe_turned_part all 9/9 build OK

## 2026-04-18 (session 3)

- Standardized all 80 families:
  - Easy wins (already table-driven, just needed `standard =`): i_beam (EN 10034), u_channel (EN 10279), clevis_pin (ISO 2340)
  - Added tables: coil_spring (DIN 2095 wire diameters), t_pipe_fitting (ASME B16.9 NPS), clevis (DIN 71751)
  - Added `din6885a_keyway()` helper to base.py (shared by bevel_gear, sprocket, and others)
  - All 44 custom/application-specific families set to standard = "N/A"
- Launched batch_2k_apr18: 2000 samples, all 80 families, seed 2418, 8 workers
