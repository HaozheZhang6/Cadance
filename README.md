# Cadance Platform

Engineering design automation using hypergraph-based multi-agent architecture.

## Quick Start

```bash
# 1. Install core dependencies
uv sync

# 2. Set API keys (copy .env.example to .env and fill in values)
cp .env.example .env   # then edit .env

# 3. Run
uv run python -m src.cli --intent "Design a mounting bracket for a 5kg load"
```

### API Keys (.env)

Copy `.env.example` to `.env` and set the following:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (primary for data gen + intent pipeline) |
| `OPENAI_API_KEY1` | Alternate OpenAI key for key rotation |
| `OPENAI_MODEL` | Default model (e.g. `gpt-4o`) |
| `ZHIPU_API_KEY` | Zhipu AI (ZAI) key — fallback provider for data generation |
| `HYPERGRAPH_STORE_PATH` | Path for persisting the hypergraph store |

> **Note:** All keys live in `.env` (git-ignored). Never commit secrets.
> The data pipeline loads `.env` automatically via `python-dotenv`.

### Optional: Vision Rendering for Intent-to-CAD

Vision-based geometry evaluation is **optional**. The `[vision]` extra is **not** included in `uv sync` by default.

To enable vision evaluation, install **ONE** of the following:

**Option 1 (Recommended): Inkscape**
```bash
brew install inkscape
# No Python packages needed - inkscape CLI is used directly
```

**Option 2: librsvg (rsvg-convert)**
```bash
brew install librsvg
# No Python packages needed - rsvg-convert CLI is used directly
```

**Option 3: cairosvg (Python library, requires C library)**
```bash
# First install Cairo C library via Homebrew
brew install cairo

# Then install Python vision extra
uv sync --extra vision
```

**Note**: If no converter is installed, vision evaluation will gracefully skip with a warning. The pipeline will still complete successfully using rule-based evaluation.

**Troubleshooting**: If vision rendering fails, see [docs/VISION_RENDERING_TROUBLESHOOTING.md](docs/VISION_RENDERING_TROUBLESHOOTING.md)

## How It Works

**Intent Refinement Pipeline:**

```
User Intent ("Design a mounting bracket for 5kg load")
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 1: G→R→S Hierarchical Tree        │
│  ├── Goals → Requirements → Specs       │
│  └── Iterative free-text feedback       │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 2: Contract Extraction            │
│  ├── Spec citations + regime screening  │
│  └── SATISFIES edges to requirements    │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 2.5: Pre-Artifact Gate            │
│  ├── V0+V1: Schema + domain rules       │
│  ├── V3: IEEE 830 syntactic (specs/reqs)│
│  ├── V4: Z3 SAT (cross-spec + contract) │
│  ├── Hard/soft fail categorization      │
│  ├── Regen loop (up to 3x) + auto-repair│
│  └── --auto stops on gate failure       │
└─────────────────────────────────────────┘
    │ PASS
    ▼
┌─────────────────────────────────────────┐
│  Step 3: Artifact Generation            │
│  ├── LLM generates ops_program from specs│
│  └── CadQuery/FreeCAD geometry validation│
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 4: Mechanical Verification        │
│  ├── DFM checks (holes, walls, fillets) │
│  └── Evidence/Unknown node creation     │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 4.5: DFM Optimization (NLopt)     │
│  └── Parameter optimization if DFM viols│
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 5: Verification (V0+V1)           │
│  ├── Schema checks on all node types    │
│  └── Domain rules + contract gating     │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│  Step 6: Auto-Refinement (if VIOLATED)  │
│  ├── LLM suggests design fixes          │
│  └── Re-verify until SATISFIED          │
└─────────────────────────────────────────┘
    │
    ▼
Hypergraph (nodes, edges, full traceability)
```

See [Dataflow Diagram](docs/intent-refinement/dataflow-z3-branch.md) for detailed data flowing between steps.

## Output Structure

| Node Type | Description | Created By |
|-----------|-------------|------------|
| Intent | Root-level user intent | refine-grs |
| Goal | High-level goal (ACHIEVE/MAINTAIN/AVOID type) | refine-grs |
| Requirement | Engineering requirements (SHALL format) | refine-grs |
| Specification | Derived spec with parameters and tolerances | refine-grs |
| Contract | Interface contracts (assumptions → guarantees) | extract-contracts |

**Additional node types:**
| Node Type | Description | Created By |
|-----------|-------------|------------|
| Artifact | Design artifacts (ops_program, STEP files) | artifact-gen |
| Evidence | Verification evidence from mech checks | mech-verify |
| Unknown | Unresolved verification items | mech-verify |
| ToolInvocation | Records of tool executions | mech-verify |

Other types: Budget, Softgoal, Obstacle

## Graph Relationships

```
Intent ←─[DERIVES_FROM]── Goal ──[HAS_CHILD]→ Requirement ──[HAS_CHILD]→ Specification
                                                   ↑
                                                   └──[SATISFIES]── Contract

Contract ──[HAS_CHILD]→ Unknown
    └──[VALIDATES]── Evidence
```

## CLI Commands

### Intent Refinement Pipeline
```bash
# Full pipeline (--intent runs all 6 steps, interactive)
uv run python -m src.cli --intent "Design a mounting bracket for a 5kg load"

# Non-interactive mode (auto-accepts all steps)
uv run python -m src.cli --intent "Design a mounting bracket" --auto

# Verbose output (SAT details, per-contract breakdown, witness values)
uv run python -m src.cli --intent "..." --auto --verbose

# Debug logging
uv run python -m src.cli --intent "..." --auto --debug

# Skip cache (for testing new implementations)
uv run python -m src.cli --intent "..." --auto --no-cache

# Force re-run (ignore cache hit, still stores result)
uv run python -m src.cli --intent "..." --force-run

# With explicit artifact (skips auto-generation)
uv run python -m src.cli pipeline --intent "..." --artifact ops_program.json

# Step-by-step (interactive)
uv run python -m src.cli refine-grs --intent "..."     # G→R→S tree
uv run python -m src.cli extract-contracts              # Contracts from GRS
uv run python -m src.cli verify                         # Run verification
```

### DAG Multi-Agent Orchestrator
```bash
# Wave-scheduled DAG execution (intent → decomp → CAD → verify)
uv run python -m src.cli dag-run --intent "Design a mounting bracket for a 5kg load" --auto

# Alias
uv run python -m src.cli multi-agent --intent "Design a mounting bracket for a 5kg load" --auto

# Offline deterministic mode (no API calls)
uv run python -m src.cli dag-run --intent "Design a mounting bracket for a 5kg load" --auto --mock-llm
```

**Overview:** The DAG orchestrator builds a coupling-aware execution graph, spins up
Decomposition/CAD/Verifier agents, and persists run artifacts to `agent_runs/`.
Mock mode uses deterministic fixtures to keep tests fast and offline.

### Graph Inspection
```bash
uv run python -m src.cli show-graph                      # View full hypergraph state
uv run python -m src.cli show-node <id>                  # View specific node details
uv run python -m src.cli list-nodes                      # List all nodes
uv run python -m src.cli list-nodes goal                 # List goals only
uv run python -m src.cli list-nodes requirement          # List requirements only
uv run python -m src.cli list-nodes specification        # List specifications only
uv run python -m src.cli list-nodes contract --full      # Contracts with full details
uv run python -m src.cli confidence-tree                 # View confidence propagation
uv run python -m src.cli export -o out.json              # Export graph to JSON
```

### Verification
```bash
uv run python -m src.cli verify                          # Run verification pipeline
```

### Cache Management
```bash
uv run python -m src.cli cache list                      # List cached intents
uv run python -m src.cli cache stats                     # Show statistics
uv run python -m src.cli cache clear                     # Clear all
```

### Mechanical Verification
```bash
# Verify STEP parts/assemblies
mech-verify verify part.step -o ./output

# With PMI requirement
mech-verify verify part.step --require-pmi -o ./output

# With ops program (for DFM checks with explicit features)
mech-verify verify part.step --ops-program ops.json -o ./output

# With external tools (FreeCAD/SFA)
mech-verify verify part.step --use-external-tools -o ./output

# With SHACL validation
mech-verify verify part.step --shacl -o ./output

# Assembly verification (multi-part STEP)
mech-verify verify assembly.step -o ./output

# See docs/MECH_VERIFIER.md for full documentation
```

## Project Structure

```
src/
├── cli.py                   # CLI entry point
├── config.py                # Environment config
├── agents/
│   ├── grs_refinement.py    # G→R→S tree generation with feedback
│   ├── contract_extraction.py # Contract extraction from GRS
│   ├── llm.py               # OpenAI client
│   └── schemas.py           # Pydantic schemas for LLM output
├── hypergraph/
│   ├── models.py            # Node/Edge types
│   ├── engine.py            # Graph operations
│   └── store.py             # JSON persistence
├── memory/
│   └── intent_cache.py      # mem0 + ChromaDB intent caching
├── verification/
│   ├── pipeline.py          # Tiered verification (V0–V4)
│   ├── syntactic/           # V3: IEEE 830 + schema rules
│   └── semantic/            # V4: Z3 SAT, unit canonicalization, symbol tables
├── verifier_core/           # Domain-agnostic verification framework
├── mech_verifier/           # Mechanical verification (STEP/CAD)
└── uncertainty/
    └── propagation.py       # Confidence propagation
```

## Development

```bash
uv run pytest              # Run tests
uv run black .             # Format code
uv run ruff check .        # Lint
```

## Documentation

### Core Documentation
- [End-to-End Pipeline](docs/end_to_end/README.md) - Intent to verification flow
- [Memory Layer](docs/MEMORY_LAYER.md) - Intent caching with mem0 + ChromaDB
- [Verifier Core Overview](docs/VERIFIER_CORE.md) - Domain-agnostic verification framework
- [Mech Verifier Overview](docs/MECH_VERIFIER.md) - Mechanical verification (STEP/assembly/DFM/PMI)
- [EDA Verifier Overview](docs/EDA_VERIFIER.md) - Electronic design verification (PCB/schematic/CDS)

### Module-Specific
- [Verifier Core README](src/verifier_core/README.md) - Core models and API
- [Mech Verifier README](src/mech_verifier/README.md) - Mech quick start and API
- [Mech Verifier Architecture](src/mech_verifier/ARCHITECTURE.md) - System architecture
- [Mech Verifier Data Flow](src/mech_verifier/DATAFLOW.md) - Data flow diagrams
- [EDA Verifier README](src/eda_verifier/README.md) - EDA framework detailed docs
- [Tools Framework](src/tools/README.md) - CadQuery gateway and subprocess isolation
