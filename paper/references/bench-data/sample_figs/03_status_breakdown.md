# 03_status_breakdown

**Reference papers:** `mmlu_pro`, `mmsi_bench`, `webarena_verified`
**Role in source:** construction-quality transparency — count rejections, list reasons.
**Our implementation:** synth_parts.csv → status pie + reject_reason top-8 horizontal bars.
**Storyline contribution:** Reviewer-pleaser: shows we throw away bad data rather than ship it. Mirrors mmlu_pro Table 1 issue counts (350 incorrect / 1953 false-neg / 862 bad-format).

