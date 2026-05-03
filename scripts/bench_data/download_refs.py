#!/usr/bin/env python3
"""Download 60 reference PDFs to paper/references/bench-data/<slug>/raw.pdf.

[have] papers (11) are copied from paper/references/<slug>_*.pdf.
The rest are resolved (openreview/arxiv/proceedings) and downloaded in parallel.
"""

import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "paper/references/bench-data"
LOCAL = ROOT / "paper/references"
LOG = OUT / "download.log"

HAVE = {
    "text2cad": "text2cad_2024.pdf",
    "cad_coder": "cad_coder_2025.pdf",
    "cad_recode": "cad_recode_2025.pdf",
    "cadrille": "cadrille_2025.pdf",
    "cadevolve": "cadevolve_2026.pdf",
    "cadcodeverify": "cadcodeverify_2025.pdf",
    "autocodebench": "autocodebench_2026.pdf",
    "infinity_chat": "infinity_chat_2025.pdf",
    "mmsi_bench": "mmsi_bench_2026.pdf",
    "sportr": "sportr_2026.pdf",
    "sportu": "sportu_2025.pdf",
}


def resolve_pdf_url(url: str) -> str:
    if url.startswith("https://arxiv.org/abs/"):
        return url.replace("/abs/", "/pdf/") + ".pdf"
    if url.startswith("https://openreview.net/forum"):
        return url.replace("/forum", "/pdf")
    if url.endswith(".pdf"):
        return url
    if "Abstract" in url and url.endswith(".html"):
        return (
            url.replace("/hash/", "/file/")
            .replace("-Abstract-Conference.html", "-Paper-Conference.pdf")
            .replace(
                "-Abstract-Datasets_and_Benchmarks_Track.html",
                "-Paper-Datasets_and_Benchmarks_Track.pdf",
            )
        )
    return url


def parse_candidates() -> list[tuple[str, str]]:
    text = (OUT / "CANDIDATES.md").read_text()
    rows = []
    for line in text.splitlines():
        m = re.match(r"\|\s*\d+\s*\|\s*(\w+)\s*\|[^|]*\|[^|]*\|[^|]*\|\s*(\S+)\s*\|", line)
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def download_one(slug: str, url: str) -> str:
    d = OUT / slug
    d.mkdir(parents=True, exist_ok=True)
    target = d / "raw.pdf"
    if target.exists() and target.stat().st_size > 0:
        return f"SKIP {slug} (exists)"
    if slug in HAVE:
        src = LOCAL / HAVE[slug]
        if src.exists():
            shutil.copy(src, target)
            return f"HAVE {slug} {target.stat().st_size}"
    pdf_url = resolve_pdf_url(url)
    try:
        r = subprocess.run(
            [
                "curl", "-sL", "-A", "Mozilla/5.0",
                "-o", str(target),
                "-w", "%{http_code}",
                "--max-time", "60",
                pdf_url,
            ],
            capture_output=True, text=True, timeout=90,
        )
        code = r.stdout.strip()
        if code == "200" and target.exists():
            with open(target, "rb") as f:
                head = f.read(4)
            if head == b"%PDF":
                return f"OK   {slug} {target.stat().st_size} {pdf_url}"
        target.unlink(missing_ok=True)
        return f"FAIL {slug} code={code} url={pdf_url}"
    except Exception as e:
        target.unlink(missing_ok=True)
        return f"FAIL {slug} exc={e!r} url={pdf_url}"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = parse_candidates()
    print(f"Parsed {len(rows)} rows", file=sys.stderr)
    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(download_one, s, u): s for s, u in rows}
        for fut in as_completed(futs):
            r = fut.result()
            results.append(r)
            print(r, file=sys.stderr)
    LOG.write_text("\n".join(sorted(results)) + "\n")
    n = {k: sum(1 for r in results if r.startswith(k)) for k in ("OK", "HAVE", "FAIL", "SKIP")}
    summary = f"\n=== summary === OK:{n['OK']} HAVE:{n['HAVE']} FAIL:{n['FAIL']} SKIP:{n['SKIP']}\n"
    LOG.write_text(LOG.read_text() + summary)
    print(summary, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
