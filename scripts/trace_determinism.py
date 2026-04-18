#!/usr/bin/env python
"""Trace outputs at each pipeline stage to find divergence point.

Run with: uv run python scripts/trace_determinism.py

Records at each stage:
1. ops_program (LLM-generated operations JSON)
2. decomposition (CADIntentParser output)
3. final_code (CodeGenerator + feedback loop output)
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def hash_content(content: str) -> str:
    """Get short hash of content."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def run_traced_pipeline(run_id: int, seed: int = 42, temperature: float = 0.0):
    """Run pipeline with tracing at each stage."""
    import openai

    from src.config import OPENAI_MODEL
    from src.hypergraph.store import HypergraphStore

    traces = {}

    print(f"\n{'='*60}")
    print(f"RUN {run_id} (seed={seed}, temp={temperature}, model={OPENAI_MODEL})")
    print(f"{'='*60}")

    # Load hypergraph to get specs
    store = HypergraphStore("data/hypergraph.json")
    nodes, edges = store.load()

    # Find specification nodes
    from src.hypergraph.models import SpecificationNode

    spec_nodes = [n for n in nodes.values() if isinstance(n, SpecificationNode)]
    if not spec_nodes:
        print("ERROR: No specification nodes found")
        return traces

    # Build specs text (same as ops_generator does)
    specs_text = "\n".join([f"- {node.description}" for node in spec_nodes])

    # =========================================================================
    # STAGE 1: Ops Program Generation (same as OpsGeneratorAgent.generate_from_specs)
    # =========================================================================
    print("\n[Stage 1] Generating ops_program...")

    client = openai.OpenAI()

    # Use same template as ops_generator.py
    system_prompt = """You are a mechanical design expert. Generate an ops_program JSON that represents
a manufacturable design based on the given specifications.

The ops_program format is:
```json
{
  "schema_version": "ops_program.v1",
  "name": "part_name",
  "description": "Part description",
  "material": "material specification",
  "units": "mm",
  "stock": {
    "type": "block",
    "dimensions": {"x": 100, "y": 50, "z": 20}
  },
  "operations": [
    {
      "id": "op_001",
      "primitive": "hole|pocket|slot|groove|fillet|chamfer|shell|rib|boss",
      "description": "Operation description",
      "parameters": [
        {"name": "param_name", "value": 10.0, "unit": "mm"}
      ],
      "position": {"x": 0, "y": 0, "z": 0},
      "annotations": {}
    }
  ],
  "dfm_status": "DRAFT",
  "revision_notes": []
}
```

Generate a complete, valid ops_program JSON that satisfies all requirements.
Respond with ONLY the JSON, no explanation."""

    user_prompt = f"""DESIGN REQUIREMENTS:
{specs_text}

DFM GUIDELINES:
- Hole diameter: minimum 0.5mm
- Hole L/D ratio: maximum 10:1
- Fillet radius: minimum 0.2mm
- Wall thickness: minimum 1.0mm (metal), 1.5mm (plastic)
- Slot width: minimum 0.5mm
- Pocket corner radius: minimum 1/3 of depth

REQUIRED PARAMETERS FOR EACH PRIMITIVE:
- hole: MUST include "diameter" and "depth" parameters
- fillet: MUST include "radius" parameter
- chamfer: MUST include "distance" or "angle" parameter
- pocket: MUST include "width", "length", "depth", and "corner_radius" parameters
- slot: MUST include "width" and "length" parameters"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_completion_tokens=4000,
        seed=seed,
        response_format={"type": "json_object"},
    )

    ops_program_str = response.choices[0].message.content
    ops_hash = hash_content(ops_program_str)
    traces["ops_program"] = {"hash": ops_hash, "content": ops_program_str}

    print(f"  Hash: {ops_hash}")
    print(f"  Fingerprint: {response.system_fingerprint}")

    # Parse and show operations
    ops_program = json.loads(ops_program_str)
    operations = ops_program.get("operations", [])
    print(f"  Operations ({len(operations)}):")
    for op in operations:
        print(f"    - {op.get('id')}: {op.get('primitive')}")

    # =========================================================================
    # STAGE 2: Decomposition (CADIntentParser)
    # =========================================================================
    print("\n[Stage 2] Decomposition (CADIntentParser)...")

    from src.agents.ops_generator import _OpenAIClientAdapter
    from src.cad.intent_decomposition.operations.intent_parser import CADIntentParser

    adapter = _OpenAIClientAdapter(client, model=OPENAI_MODEL)
    parser = CADIntentParser(llm=adapter)

    # Build intent string from ops_program (same as _ops_program_to_intent)
    intent = f"""Create CadQuery geometry from this ops_program:

{json.dumps(ops_program, indent=2)}

DFM CONSTRAINTS:
- Hole diameter: minimum 0.5mm
- Fillet radius: minimum 0.2mm

Generate Python code that:
1. Creates the stock geometry
2. Applies each operation
3. Assigns final geometry to variable named 'result'"""

    # Parse intent
    try:
        parsed_ops = parser.parse(intent)

        # Serialize parsed operations
        decomp_data = {
            "overall_confidence": parsed_ops.overall_confidence,
            "num_operations": len(parsed_ops.operations),
            "operations": [
                {
                    "primitive": op.primitive.value,
                    "description": op.description,
                    "confidence": op.confidence,
                    "params": [
                        {"name": p.name, "value": p.value, "unit": p.unit}
                        for p in op.parameters
                    ],
                }
                for op in parsed_ops.operations
            ],
        }
        decomp_str = json.dumps(decomp_data, indent=2, sort_keys=True)
        decomp_hash = hash_content(decomp_str)
        traces["decomposition"] = {"hash": decomp_hash, "content": decomp_str}

        print(f"  Hash: {decomp_hash}")
        print(f"  Confidence: {parsed_ops.overall_confidence:.2f}")
        print(f"  Parsed operations ({len(parsed_ops.operations)}):")
        for op in parsed_ops.operations:
            print(f"    - {op.primitive.value}: {op.description[:50]}...")

    except Exception as e:
        print(f"  FAILED: {e}")
        traces["decomposition"] = {"hash": "FAILED", "content": str(e)}
        return traces

    # =========================================================================
    # STAGE 3: Full Pipeline (synthesis + execution)
    # =========================================================================
    print("\n[Stage 3] Full Pipeline (synthesis + execution)...")

    from src.cad.intent_decomposition.pipeline import (
        IntentToCADPipeline,
        PipelineConfig,
    )
    from src.cad.intent_decomposition.retrieval.api_catalog import CadQueryAPICatalog
    from src.cad.intent_decomposition.retrieval.embeddings import OpenAIEmbeddingClient
    from src.tools.gateway import SubprocessCadQueryBackend, ToolGateway

    # Initialize components
    api_catalog = CadQueryAPICatalog()
    embedding_client = OpenAIEmbeddingClient()

    backend = SubprocessCadQueryBackend()
    gateway = ToolGateway()
    gateway.register("cadquery", backend)

    config = PipelineConfig(
        max_feedback_iterations=3,
        code_gen_temperature=temperature,
        code_gen_seed=seed,
    )

    pipeline = IntentToCADPipeline(
        llm_client=adapter,
        api_catalog=api_catalog,
        embedding_client=embedding_client,
        config=config,
        gateway=gateway,
    )

    # Run pipeline
    result = pipeline.run(intent)

    if result.success and result.final_code:
        code_hash = hash_content(result.final_code)
        traces["final_code"] = {"hash": code_hash, "content": result.final_code}

        print(f"  Hash: {code_hash}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Stages: {len(result.stages)}")
        print("  Code preview:")
        for line in result.final_code.split("\n")[:10]:
            print(f"    {line}")
        if len(result.final_code.split("\n")) > 10:
            print(f"    ... ({len(result.final_code.split(chr(10)))} lines)")
    else:
        error = result.stages[-1].error if result.stages else "Unknown error"
        traces["final_code"] = {"hash": "FAILED", "content": error}
        print(f"  FAILED: {error}")

    return traces


def compare_runs(all_traces: list[dict]):
    """Compare traces across runs to find divergence."""
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)

    stages = ["ops_program", "decomposition", "final_code"]
    divergence_found = False

    for stage in stages:
        hashes = []
        for traces in all_traces:
            h = traces.get(stage, {}).get("hash", "N/A")
            hashes.append(h)

        unique = len(set(hashes))
        match = "IDENTICAL" if unique == 1 else f"DIFFER ({unique} unique)"

        print(f"\n{stage}:")
        for i, h in enumerate(hashes):
            print(f"  Run {i+1}: {h}")
        print(f"  -> {match}")

        if unique > 1 and not divergence_found:
            print(f"\n  *** FIRST DIVERGENCE at {stage} ***")
            divergence_found = True

            # Show diff preview
            contents = [
                all_traces[i].get(stage, {}).get("content", "")
                for i in range(len(all_traces))
            ]
            if all(contents):
                print("\n  Content preview (first 500 chars):")
                for i, c in enumerate(contents):
                    print(f"\n  --- Run {i+1} ---")
                    print(f"  {c[:500]}...")


def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set")
        sys.exit(1)

    print("Determinism Trace Analysis")
    print("Tracing 3 runs through pipeline stages...")
    print("Each run uses seed=42, temperature=0.0")

    all_traces = []
    for run_id in range(1, 4):
        traces = run_traced_pipeline(run_id, seed=42, temperature=0.0)
        all_traces.append(traces)

    compare_runs(all_traces)

    # Save full traces
    output = {f"run_{i+1}": traces for i, traces in enumerate(all_traces)}
    with open("/tmp/determinism_traces.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\n\nFull traces saved to: /tmp/determinism_traces.json")


if __name__ == "__main__":
    main()
