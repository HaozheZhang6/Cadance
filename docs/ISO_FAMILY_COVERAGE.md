# ISO Family Coverage

**77 families total** — last updated 2026-04-17 (session 2)

## Summary

| Status | Count | Families |
|--------|-------|---------|
| ✅ Exact standard table | 21 | bolt, hex_nut, washer, sprocket, circlip, dowel_pin, i_beam, u_channel, shaft_collar, handwheel, t_slot_rail, parallel_key, clevis_pin, taper_pin, hex_standoff, hollow_tube, bearing_retainer_cap + 3 gears |
| ⚙️ Tagged / approx constrained | 9 | coil_spring, pipe_flange, round_flange, t_pipe_fitting, stepped_shaft, mounting_plate, slotted_plate, waffle_plate, pulley |
| — No applicable ISO | 49 | everything else |

---

## ✅ Exact Standard Table (sampler draws only from table rows)

| Family | Standard | Table | Difficulty split |
|--------|----------|-------|-----------------|
| `spur_gear` | ISO 54, ISO 53 | R20/R40 module series | easy=small-m, hard=large-m |
| `helical_gear` | ISO 54, ISO 53 | same | same |
| `bevel_gear` | ISO 54, ISO 23509 | same | same |
| `worm_screw` | ISO 54, ISO 1122 | same | same |
| `sprocket` | ISO 606 | pitch {6.35, 8, 9.525, 12.7, 15.875, 19.05, 25.4} mm | easy=small-pitch |
| `bolt` | ISO 4014 + ISO 888 | M3–M48 (18 rows) + preferred lengths | easy=M3–M12 |
| `hex_nut` | ISO 4032 | M3–M48 (18 rows) | easy=M3–M12 |
| `washer` | ISO 7089/7090 | M5–M64 (23 rows); easy=plain, medium/hard=chamfered | easy=M5–M20 preferred |
| `dowel_pin` | ISO 8734 | ⌀{1,1.5,2,2.5,3,4,5,6,8,10,12,16,20} mm | easy=small-d |
| `circlip` | DIN 471 | shaft_d {8,10,12,15,17,19,20,22,24,25,28,30,35,40,45,50,55,60,70,80} mm | easy=small |
| `i_beam` | EN 10034 (IPE) | IPE80–IPE600 (18 rows) | easy=IPE80–200 |
| `u_channel` | EN 10279 (UPN) | UPN30–UPN300 (16 rows) | easy=UPN30–100 |
| `shaft_collar` | DIN 705 | 24 rows bore 6–100 mm | easy=6–25, medium=16–50, hard=all |
| `handwheel` | DIN 950 | 8 rows OD 80–400 mm | easy=80–160, medium=125–250, hard=all |
| `t_slot_rail` | ISO 299 | 8 slot widths 8–28 mm | easy=8–12, medium=8–18, hard=all |
| `parallel_key` | DIN 6885A | 20 rows shaft 6–230 mm | easy=small shaft, hard=all |
| `clevis_pin` | ISO 2340 | 16 rows d 4–40 mm | easy=d≤12, medium=8–24, hard=all |
| `taper_pin` | ISO 2339 | 14 rows d_nom 1–20 mm | easy=d≤5, medium=3–12, hard=all |
| `hex_standoff` | ISO 272 / DIN 934 | 9 rows M3–M20; AF+bore from table | easy=M3–M8, medium=M5–M12, hard=all |
| `hollow_tube` | EN 10219 | 10 SHS + 10 RHS sizes (20×20×2 – 200×150×6) | easy=SHS 20–50 |
| `bearing_retainer_cap` | ISO 15 / 62xx | 16 rows bore 10–80 mm; boss OD ≥ bearing OD | easy=bore 10–20, hard=all |
| `pulley` | ISO 22 / ISO 4183 | groove angle ∈ {34°,36°,38°} | medium/hard only |

---

## ⚙️ Tagged / Approx (iso_tags set, geometry ~correct)

| Family | Standard | What's constrained |
|--------|----------|--------------------|
| `coil_spring` | ISO 2162-1 | spring index C = D/d ∈ [4,20] |
| `pipe_flange` | ISO 7005-1 | n_bolts, PN class tag |
| `round_flange` | ISO 7005-1 | same |
| `t_pipe_fitting` | ISO 1127 | wall/OD ratio range |
| `stepped_shaft` | ISO 286-1 | IT grade tag |
| `shaft_collar` | ISO 286-1 | IT grade tag |
| `mounting_plate` | ISO 2768-1 | tolerance class tag |
| `slotted_plate` | ISO 2768-1 | same |
| `waffle_plate` | ISO 2768-1 | same |

---

## 🔲 Remaining gaps

*(none — all high-priority gaps resolved)*

---

## — No applicable ISO (54 families)

`ball_knob`, `bellows`, `bucket`, `cable_routing_panel`, `cam`, `capsule`,
`chair`, `clevis`, `connecting_rod`, `connector_faceplate`, `cruciform`,
`dog_bone`, `dome_cap`, `dovetail_slide`, `duct_elbow`, `enclosure`,
`fan_shroud`, `flat_link`, `gusseted_bracket`, `heat_sink`, `hinge`,
`hollow_tube`, `impeller`, `knob`, `l_bracket`, `lathe_turned_part`,
`locator_block`, `manifold_block`, `mesh_panel`, `motor_end_cap`,
`mounting_angle`, `nozzle`, `pcb_standoff_plate`, `pipe_elbow`, `piston`,
`propeller`, `ratchet_sector`, `rect_frame`, `rib_plate`, `sheet_metal_tray`,
`snap_clip`, `spacer_ring`, `standoff`, `star_blank`, `table`, `tapered_boss`,
`threaded_adapter`, `torus_link`, `vented_panel`, `waffle_plate`\*, `wire_grid`,
`z_bracket`, `mounting_plate`\*, `slotted_plate`\*

(\* these have ISO 2768 tolerance tags but no geometric constraints)

---

## Change log

| Date | Change |
|------|--------|
| 2026-04-07 | Added sprocket, circlip, dowel_pin; bolt ISO 4014 table |
| 2026-04-17 | Added washer (merged plain+chamfered); hex_nut/i_beam/u_channel exact tables |
| 2026-04-17 | Added parallel_key (DIN 6885A), clevis_pin (ISO 2340), taper_pin (ISO 2339) |
| 2026-04-17 | shaft_collar DIN 705, handwheel DIN 950, t_slot_rail ISO 299 exact tables |
| 2026-04-17 | hex_standoff ISO 272, hollow_tube EN 10219, bearing_retainer_cap ISO 15 |
| 2026-04-17 | pulley ISO 22 groove angle {34°,36°,38°}; spur_gear ISO 54 module series |
| 2026-04-17 | Total: 21 exact-table families (up from 5), 0 remaining high-priority gaps |

**COMMENT**

## 1) 可以新增的 ISO family

| Family                           | Candidate standard   | Constraint type                             | Suggested status | Source                      |
| -------------------------------- | -------------------- | ------------------------------------------- | ---------------- | --------------------------- |
| `plain_bushing` / `wrapped_bush` | ISO 3547-1           | `ID, OD, L`, 可加 flange 版本                   | exact table      | ISO official ([ISO][1])     |
| `clevis_pin`                     | ISO 2340 / ISO 2341  | `d, l, head/no-head, split-pin-hole`        | exact table      | ISO official ([ISO][2])     |
| `split_pin`                      | ISO 1234             | `d, l` 离散系列                                 | exact table      | ISO official ([ISO][3])     |
| `slotted_spring_pin`             | ISO 8752 / ISO 13337 | `d, l`, heavy/light duty                    | exact table      | ISO official ([Norelem][4]) |
| `taper_pin`                      | ISO 2339             | nominal `d, l`, taper 固定                    | exact table      | ISO official ([ISO][5])     |
| `taper_pin_external_thread`      | ISO 8737             | nominal `d, l`, thread size                 | exact table      | ISO official ([ISO][6])     |
| `taper_pin_internal_thread`      | ISO 8736             | nominal `d, l`, thread size                 | exact table      | ISO official ([ISO][7])     |
| `grooved_pin`                    | ISO 8740             | nominal `d, l`, full-length diamond grooves | exact table      | ISO official ([ISO][8])     |

## 2) 现有 family 里，可能可以补 ISO 标准的

| Family                 | Candidate standard  | Constraint type                                          | Suggested status       | Source                   |
| ---------------------- | ------------------- | -------------------------------------------------------- | ---------------------- | ------------------------ |
| `bearing_retainer_cap` | ISO 15              | bearing seat / bore / OD series                          | partial exact          | ISO official ([ISO][9])  |
| `hollow_tube`          | ISO 1127            | `OD × wall_thickness` 离散系列                               | exact table            | ISO official ([ISO][10]) |
| `pipe_elbow`           | ISO 49 + ISO 7-1    | nominal size + thread designation + 45°/90° family       | tagged / partial exact | ISO official ([ISO][11]) |
| `threaded_adapter`     | ISO 7-1 / ISO 228-1 | male/female thread designation, parallel vs taper thread | tagged / partial exact | ISO official ([ISO][12]) |
| `pulley`               | ISO 4183            | belt section + groove dimensions + pulley family         | exact table            | ISO official ([ISO][13]) |
| `t_slot_rail`          | ISO 299             | slot width / spacing / mating bolt sizes                 | exact table            | ISO official ([ISO][14]) |
| `t_pipe_fitting`       | ISO 49 + ISO 7-1    | nominal size + thread family；几何细节可弱化                     | tagged                 | ISO official ([ISO][11]) |
| `shaft_collar`         | ISO 286-1           | fit / IT grade tag，不适合主导全部几何                             | tagged                 | ISO official ([ISO][9])  |

## 3) 现有 family 里，可能更适合加其他工业级标准的

| Family                        | Candidate standard | Constraint type                     | Suggested status                   | Source                        |
| ----------------------------- | ------------------ | ----------------------------------- | ---------------------------------- | ----------------------------- |
| `shaft_collar`                | DIN 705            | bore–OD–width–set-screw table       | industrial exact                   | norelem ([Norelem][15])       |
| `t_slot_rail`                 | DIN 650            | slot width discrete series          | industrial exact                   | norelem ([Norelem][16])       |
| `handwheel`                   | DIN 950            | `OD, bore, hub, spokes` 系列          | industrial exact                   | norelem ([Norelem][17])       |
| `parallel_key`                | DIN 6885 A         | `b, h, l` exact table               | industrial exact                   | norelem ([Norelem][18])       |
| `circlip` (shaft)             | DIN 471            | shaft diameter → ring geometry      | already exact / split into subtype | TraceParts ([TraceParts][19]) |
| `circlip` (bore)              | DIN 472            | bore diameter → ring geometry       | industrial exact / split subtype   | TraceParts ([TraceParts][19]) |
| `t_slot_rail` mating hardware | DIN 508            | T-slot nut dimensions by slot width | industrial exact                   | TraceParts ([TraceParts][20]) |
| `t_slot_rail` mating hardware | DIN 787            | T-slot bolt family by slot width    | industrial exact                   | TraceParts ([TraceParts][21]) |

一个例子：
`shaft_collar` 现在如果还是 `ISO 286-1`，更像只是挂了一个 `H7/g6` 这种公差标签；
如果改成 `DIN 705`，就能直接变成 **按 bore 查 OD、width、set screw 的 exact table family**。


[1]: https://www.iso.org/standard/70443.html?utm_source=chatgpt.com "ISO 3547-1:2018 - Plain bearings — Wrapped bushes"
[2]: https://www.iso.org/standard/7176.html?utm_source=chatgpt.com "ISO 2340:1986 - Clevis pins without head"
[3]: https://www.iso.org/standard/20000.html?utm_source=chatgpt.com "ISO 1234:1997 - Split pins"
[4]: https://www.norelem.com/doc/cl/pt/did.217659/PRODUKT_OVERVIEW_EDITION_2020_EN_doppelseitig.pdf?utm_source=chatgpt.com "THE BIG BOOK GREEN"
[5]: https://www.iso.org/standard/7174.html?utm_source=chatgpt.com "ISO 2339:1986 - Taper pins, unhardened"
[6]: https://www.iso.org/standard/16146.html?utm_source=chatgpt.com "ISO 8737:1986 - Taper pins with external thread, unhardened"
[7]: https://www.iso.org/standard/16145.html?utm_source=chatgpt.com "ISO 8736:1986 - Taper pins with internal thread, unhardened"
[8]: https://www.iso.org/standard/84083.html?utm_source=chatgpt.com "ISO 8740:2025 - Parallel grooved pins, with chamfer point"
[9]: https://www.iso.org/standard/69977.html?utm_source=chatgpt.com "ISO 15:2017 - Rolling bearings — Radial bearings"
[10]: https://www.iso.org/standard/5660.html?utm_source=chatgpt.com "ISO 1127:1992 - Stainless steel tubes"
[11]: https://www.iso.org/standard/3686.html?utm_source=chatgpt.com "ISO 49:1994 - Malleable cast iron fittings threaded to ISO 7-1"
[12]: https://www.iso.org/standard/20819.html?utm_source=chatgpt.com "ISO 7-1:1994 - Pipe threads where pressure-tight joints are ..."
[13]: https://www.iso.org/standard/88705.html?utm_source=chatgpt.com "ISO 4183:2026 - Belt drives — Classical and narrow V-belts"
[14]: https://www.iso.org/standard/4229.html?utm_source=chatgpt.com "Machine tool tables — T-slots and corresponding bolts"
[15]: https://www.norelem.com/doc/dk/en/did.92039/07800_Datasheet_4290_Shaft_collars_set_screw_DIN_705_stainless_steel_--en.pdf?utm_source=chatgpt.com "07800 Shaft collars set screw DIN 705, stainless steel"
[16]: https://www.norelem.com/doc/be/en/did.96888/03250_Datasheet_2764_Slot_keys--en.pdf?utm_source=chatgpt.com "03250 Slot keys"
[17]: https://www.norelem.com/doc/ua/en/did.93966/06271_OG_Datasheet_3515_Handwheels_DIN_950_grey_cast_iron_without_grip--en.pdf?utm_source=chatgpt.com "06271_OG Handwheels DIN 950, grey cast iron, without grip"
[18]: https://www.norelem.com/doc/ca/en/did.369520/03288_Datasheet_36380_Parallel_keys_DIN_6885_A--en.pdf?utm_source=chatgpt.com "03288 Parallel keys DIN 6885 A"
[19]: https://www.traceparts.com/en/search/din-mechanical-systems-and-components-of-general-use-fasteners-snap-rings?CatalogPath=DIN%3AC21.060.060&utm_source=chatgpt.com "Snap rings: 3D models - SOLIDWORKS, Inventor, CATIA ..."
[20]: https://www.traceparts.com/en/product/ganter-din-508-tnuts-without-thread-steel?CatalogPath=GANTER%3A12f71278-1803-4f27-91aa-81e878fd3f3a&Product=34-26112018-087188&utm_source=chatgpt.com "DIN 508 T-Nuts, without thread, Steel"
[21]: https://www.traceparts.com/en/product/ganter-din-787-tslot-bolts?CatalogPath=GANTER%3A12f71278-1803-4f27-91aa-81e878fd3f3a&Product=68-24092007-654682&utm_source=chatgpt.com "GANTER - Free CAD models - DIN 787 T-Slot bolts"
