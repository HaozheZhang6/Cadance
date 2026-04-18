"""LLM-based reverse decomposition: CadQuery code -> ops_program.v1 operations."""

from __future__ import annotations

import logging
import time
from typing import Any

from src.agents.llm import LLMClient

logger = logging.getLogger(__name__)

CODE_TO_OPS_SYSTEM_PROMPT = """\
You are a CAD reverse-engineering system. Given CadQuery Python code that builds \
a 3D part, extract the manufacturing operations into an ops_program.v1 JSON.

## Output Format
Return ONLY valid JSON:
{
  "operations": [
    {
      "id": "op_001",
      "primitive": "<primitive_name>",
      "description": "<what this does, max 15 words>",
      "parameters": [
        {"name": "<param>", "value": <number>, "unit": "mm"}
      ],
      "position": {"x": 0, "y": 0, "z": 0},
      "annotations": {}
    }
  ],
  "overall_confidence": <0.0-1.0>,
  "ambiguities": [],
  "assumptions": [],
  "stock_suggestion": {
    "type": "block" | "cylinder" | "polygon",
    "dimensions": {}
  }
}

## Primitive Mapping (CadQuery -> ops_program)
- .box(x,y,z) -> STOCK (not an operation). Report in stock_suggestion.
- .circle(r).extrude(h) as first op -> STOCK (cylinder). Report in stock_suggestion.
- .polygon(n,r).extrude(h) as first op -> STOCK (polygon). Report in stock_suggestion.
- .circle(r).cutThruAll() -> "hole" with diameter=2*r, depth="through"
- .hole(d) / .hole(d, depth) -> "hole"
- .rect(w,h).cutThruAll() -> "pocket" (through)
- .rect(w,h).cutBlind(d) -> "pocket" with depth=d
- .rect(w,h).extrude(h) on existing body -> "boss" or "rib" (additive feature)
- .fillet(r) -> "fillet" with radius=r
- .chamfer(d) -> "chamfer" with distance=d
- .shell(t) -> "shell" with thickness=t
- .cboreHole(...) -> "hole_counterbore"
- .cskHole(d, cd, ca) -> "hole_countersink"
- .polyline([...]).close().extrude(h) -> "extrude" with profile="polyline"
- .loft(...) -> "loft"
- .revolve(...) -> "revolve"
- .pushPoints([...]).hole(d) -> single "hole" op with annotations.quantity + annotations.centers

## Rules
1. The FIRST geometry operation (box/circle+extrude/polygon+extrude) is STOCK, not an operation. \
Put it in stock_suggestion only.
2. Extract EXACT numeric values from the code. Never guess.
3. For .circle(r).cutThruAll(): diameter = 2 * r.
4. Combine identical repeated features into one op with annotations.quantity and annotations.centers.
5. If .faces(">Z") or similar precedes an op, note in annotations.face_selector.
6. If .edges("|Z") or similar precedes fillet/chamfer, note in annotations.edge_selector.
7. Keep descriptions factual and short (<15 words).
8. Include fillet and chamfer — they carry real parameters.
9. For .pushPoints([(x1,y1),(x2,y2)]).hole(d): one "hole" op with quantity=N and centers list.
10. Position: use coordinates from .moveTo(), .center(), .pushPoints() if available. \
Otherwise {"x":0,"y":0,"z":0}.
11. id format: "op_001", "op_002", etc.
"""

CODE_TO_OPS_USER_TEMPLATE = """\
Decompose this CadQuery code for part "{part_name}" into ops_program.v1 operations.

```python
{cadquery_code}
```

Feature descriptions from source:
{feature_comments}

Return the JSON."""


def decompose_cadquery_to_operations(
    llm_client: LLMClient,
    cadquery_code: str,
    part_name: str,
    feature_comments: list[str],
    max_retries: int = 2,
    temperature: float = 0.2,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Decompose CadQuery code into ops_program.v1 operations via LLM.

    Returns:
        (operations_list, metadata_dict) where metadata has
        overall_confidence, ambiguities, assumptions, stock_suggestion.
    """
    comments_text = (
        "\n".join(f"- {c}" for c in feature_comments) if feature_comments else "(none)"
    )

    user_prompt = CODE_TO_OPS_USER_TEMPLATE.format(
        part_name=part_name,
        cadquery_code=cadquery_code,
        feature_comments=comments_text,
    )

    last_err = None
    for attempt in range(1 + max_retries):
        try:
            t = temperature if attempt == 0 else 0.1
            result = llm_client.complete_json(
                prompt=user_prompt,
                system_prompt=CODE_TO_OPS_SYSTEM_PROMPT,
                temperature=t,
                max_tokens=4000,
            )
            operations = result.get("operations", [])
            meta = {
                "overall_confidence": result.get("overall_confidence", 0.0),
                "ambiguities": result.get("ambiguities", []),
                "assumptions": result.get("assumptions", []),
                "stock_suggestion": result.get("stock_suggestion", {}),
            }
            return operations, meta

        except ValueError:
            last_err = "json_parse_error"
            logger.warning(
                "LLM JSON parse failed (attempt %d/%d)", attempt + 1, 1 + max_retries
            )
            if attempt < max_retries:
                time.sleep(2**attempt)

        except Exception as e:
            last_err = str(e)
            logger.warning(
                "LLM call error (attempt %d/%d): %s", attempt + 1, 1 + max_retries, e
            )
            if attempt < max_retries:
                time.sleep(2**attempt)

    logger.error(
        "Decomposition failed after %d attempts: %s", 1 + max_retries, last_err
    )
    return [], {"error": last_err}
