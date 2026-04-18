"""Parse ground truth CadQuery model files from data/raw_data/models/."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GTModelFile:
    path: Path
    part_number: str = ""
    part_name: str = ""
    version: int = 1
    timestamp_utc: str = ""
    generation_model: str = ""
    status: str = ""
    cadquery_code: str = ""
    feature_comments: list[str] = field(default_factory=list)


_HEADER_MAP = {
    "Part Number": "part_number",
    "Part Name": "part_name",
    "Version": "version",
    "Timestamp UTC": "timestamp_utc",
    "Generation Model": "generation_model",
    "Status": "status",
}


def parse_gt_file(path: Path) -> GTModelFile:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    model = GTModelFile(path=path)
    code_start = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import cadquery") or stripped.startswith(
            "from cadquery"
        ):
            code_start = i
            break

        m = re.match(r"^#\s*(.+?):\s*(.+)$", stripped)
        if m:
            key, val = m.group(1).strip(), m.group(2).strip()
            if key in _HEADER_MAP:
                attr = _HEADER_MAP[key]
                if attr == "version":
                    model.version = int(val)
                else:
                    setattr(model, attr, val)

    model.part_name = model.part_name.strip("- ")

    model.cadquery_code = "\n".join(lines[code_start:]).strip()

    feature_re = re.compile(r"^#\s*Feature\s+\d+:\s*(.+)$")
    for line in lines[code_start:]:
        fm = feature_re.match(line.strip())
        if fm:
            model.feature_comments.append(fm.group(1).strip())

    return model


def parse_all_gt_files(models_dir: Path) -> list[GTModelFile]:
    files = sorted(models_dir.glob("*.py"))
    return [parse_gt_file(f) for f in files]
