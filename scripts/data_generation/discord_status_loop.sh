#!/usr/bin/env bash
# Loop: every 10min post UA-24 status snapshot to Discord.
# Usage: bash scripts/data_generation/discord_status_loop.sh &
# Stop:  pkill -f discord_status_loop

set -u
ROOT="/Users/haozhezhang_work/Documents/Projects_code/Cadance"
cd "$ROOT"
export PATH="$HOME/.local/bin:$PATH"
# Pull DISCORD_WEBHOOK_URL from zshrc
source "$HOME/.zshrc" >/dev/null 2>&1 || true

while true; do
    BATCH=$(ls data/data_generation/generated_data/fusion360 2>/dev/null | grep -c s4127 || echo 0)
    BATCH_PROC=$(pgrep -f batch_simple21_apr27 | head -1)
    BATCH_STATE="dead"
    if [[ -n "$BATCH_PROC" ]]; then
        ETIME=$(ps -p "$BATCH_PROC" -o etime= 2>/dev/null | xargs)
        BATCH_STATE="alive ($ETIME)"
    fi
    F360_RENDER=$(ls "$ROOT/tmp/fusion360_renders/" 2>/dev/null | grep -c composite || echo 0)
    DEEPCAD_RENDER=$(ls "$ROOT/tmp/deepcad_renders/" 2>/dev/null | grep -c composite || echo 0)
    PROFILES_PACK_FAMS=$(grep -c "^class Simple.*Family" scripts/data_generation/cad_synth/families/simple_profiles_pack.py 2>/dev/null || echo 0)
    CYL_PACK_FAMS=$(grep -c "^class Simple.*Family" scripts/data_generation/cad_synth/families/simple_cylindrical_pack.py 2>/dev/null || echo 0)
    BLOCK_PACK_FAMS=$(grep -c "^class Simple.*Family" scripts/data_generation/cad_synth/families/simple_blocks_pack.py 2>/dev/null || echo 0)
    MULTI_PACK_FAMS=$(grep -c "^class Simple.*Family" scripts/data_generation/cad_synth/families/simple_multi_stage_pack.py 2>/dev/null || echo 0)
    SHEET_PACK_FAMS=$(grep -c "^class Simple.*Family" scripts/data_generation/cad_synth/families/simple_sheet_sections_pack.py 2>/dev/null || echo 0)
    NEW_FAM_REGISTERED=$(uv run python3 -c "from scripts.data_generation.cad_synth.pipeline.registry import list_families; print(len([f for f in list_families() if f.startswith('simple_')]))" 2>/dev/null)
    MSG=$(printf "📊 UA-24 status\n• batch_simple21_apr27: %s/4200 · %s\n• F360 render: %s · DeepCAD render: %s\n• packs (profiles/cyl/block/multi/sheet): %s/%s/%s/%s/%s\n• registered simple_*: %s · target: ~100" "$BATCH" "$BATCH_STATE" "$F360_RENDER" "$DEEPCAD_RENDER" "$PROFILES_PACK_FAMS" "$CYL_PACK_FAMS" "$BLOCK_PACK_FAMS" "$MULTI_PACK_FAMS" "$SHEET_PACK_FAMS" "$NEW_FAM_REGISTERED")
    uv run python3 scripts/data_generation/discord_progress.py "$MSG" >/dev/null 2>&1
    sleep 300  # 5min
done
