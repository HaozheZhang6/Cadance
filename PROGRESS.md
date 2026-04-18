
## 2026-04-18 (session 3)

- UA-7 完成：8个 Tier C family 标准化修复 (240/240 qa_generator tests pass)
  - threaded_adapter: 加 ASME B1.20.1 NPT 9-row 尺寸表，替换全部 14 个 rng.uniform
  - spur_gear: z→rng.integers, face_w→b/m∈{6,8,10,12}×m, keyway→DIN 6885A
  - helical_gear: 同 spur_gear + helix_angle→choice([15,20,23,25,30])
  - bevel_gear: pitch_angle→choice([15..40]), face_w→b/m∈{4..8}×m
  - pulley: 以 ISO 4183 belt section 为锚重构 sample_params; ISO 22 PD 表驱动
  - sprocket: disc_thickness→dr×choice([0.8..1.3])
  - t_slot_rail: slot_depth/back_w/wall_t 改为 DIN 650 profile 固定值
  - hex_standoff: flange_od/bore_step 改为离散倍数
- UA-8 完成：33个有标准 family 全部在 docstring 加 Reference 来源（标准号+文档标题）
- 88 tests pass

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
