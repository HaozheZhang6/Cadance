#!/usr/bin/env python3
"""Post 15 BenchCAD sample figures to Discord, each with reference + role + impl + storyline.

Webhook URL is read from $DISCORD_WEBHOOK_URL env var (set in ~/.bashrc).
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
FIGS = ROOT / "paper/references/bench-data/sample_figs"


def parse_md(md_path: Path) -> dict:
    out = {"refs": "", "role": "", "impl": "", "storyline": ""}
    text = md_path.read_text()
    for line in text.splitlines():
        if line.startswith("**Reference papers:**"):
            out["refs"] = line.split("**", 4)[-1].strip().lstrip(": ")
        elif line.startswith("**Role in source:**"):
            out["role"] = line.split("**", 4)[-1].strip().lstrip(": ")
        elif line.startswith("**Our implementation:**"):
            out["impl"] = line.split("**", 4)[-1].strip().lstrip(": ")
        elif line.startswith("**Storyline contribution:**"):
            out["storyline"] = line.split("**", 4)[-1].strip().lstrip(": ")
    return out


def make_message(name: str, meta: dict) -> str:
    title = name.replace("_", " ").replace("-", " — ").lstrip("0123456789 ")
    return (
        f"**{name}** — _{title}_\n"
        f"📚 **Refs:** {meta['refs']}\n"
        f"🎯 **Role in source:** {meta['role']}\n"
        f"🔧 **Our implementation:** {meta['impl']}\n"
        f"📖 **Storyline contribution:** {meta['storyline']}"
    )


def post_one(webhook: str, png: Path, md: Path) -> tuple[bool, str]:
    meta = parse_md(md)
    content = make_message(png.stem, meta)
    # Discord truncates content >2000 chars
    if len(content) > 1900:
        content = content[:1897] + "…"
    with open(png, "rb") as f:
        files = {"file": (png.name, f, "image/png")}
        data = {"payload_json": json.dumps({"content": content})}
        try:
            r = requests.post(webhook, files=files, data=data, timeout=30)
            ok = r.status_code in (200, 204)
            return ok, f"{r.status_code} {r.text[:80] if not ok else ''}"
        except Exception as e:
            return False, repr(e)


def main() -> int:
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("ERROR: DISCORD_WEBHOOK_URL env var not set", file=sys.stderr)
        return 1
    pngs = sorted(FIGS.glob("*.png"))
    if not pngs:
        print(f"ERROR: no PNGs in {FIGS}", file=sys.stderr)
        return 1
    print(f"Posting {len(pngs)} figures…", file=sys.stderr)

    # opening header
    header = (
        "🚀 **BenchCAD reference-survey sample figures (15)**\n"
        "60-paper survey across NeurIPS/ICLR/ICML/CVPR/ICCV (2024–2026), "
        "synthesised in `paper/references/bench-data/META.md`. Each figure below "
        "includes the source-paper inspiration, role in those papers, our implementation, "
        "and how it serves BenchCAD's NeurIPS 2026 D&B storyline."
    )
    requests.post(webhook, json={"content": header}, timeout=30)
    time.sleep(1)

    n_ok = 0
    for png in pngs:
        md = png.with_suffix(".md")
        if not md.exists():
            print(f"SKIP {png.name} — no .md", file=sys.stderr)
            continue
        ok, msg = post_one(webhook, png, md)
        status = "OK" if ok else f"FAIL {msg}"
        print(f"  {png.name}: {status}", file=sys.stderr)
        if ok:
            n_ok += 1
        time.sleep(1.5)  # webhook rate-limit safety

    print(f"\n{n_ok}/{len(pngs)} posted", file=sys.stderr)
    return 0 if n_ok == len(pngs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
