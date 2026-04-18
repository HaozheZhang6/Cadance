#!/usr/bin/env python3
"""Test if vision pipeline detects/fixes disconnected geometry issue.

The disconnection problem: when ribs are placed using absolute coordinates
on a centered workplane, they end up off the base plate -> disconnected solids.

This test uses an intent similar to the bracket_disconnected demo to see if:
1. The pipeline generates geometry with this bug
2. The vision critic detects disconnected/floating geometry
3. The regeneration loop fixes it
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.cad.intent_decomposition.llm import LLMRouter
from src.cad.intent_decomposition.pipeline import (
    IntentToCADPipeline,
    PipelineConfig,
    VisionEvaluationConfig,
)
from src.cad.intent_decomposition.retrieval.api_catalog.cadquery_catalog import (
    CadQueryAPICatalog,
)
from src.cad.intent_decomposition.retrieval.embeddings.openai_embeddings import (
    OpenAIEmbeddingClient,
)
from src.tools.gateway import SubprocessCadQueryBackend, ToolGateway

# Enhanced logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


class LLMCallLogger:
    """Logger to track all LLM calls with input/output."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.call_count = 0
        self.calls = []
        self.workflow_events = []

    def log_call(self, stage: str, prompt: str, response: str, metadata: dict = None):
        """Log a single LLM call."""
        self.call_count += 1
        call_data = {
            "call_id": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "prompt": prompt,
            "response": response,
            "metadata": metadata or {},
        }
        self.calls.append(call_data)

        call_file = self.log_dir / f"llm_call_{self.call_count:03d}_{stage}.json"
        call_file.write_text(json.dumps(call_data, indent=2))
        logger.info(
            f"LLM Call #{self.call_count} [{stage}]: {len(prompt)} -> {len(response)} chars"
        )

    def log_workflow_event(self, event_type: str, description: str, data: dict = None):
        """Log a workflow event."""
        event = {
            "event_id": len(self.workflow_events) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "description": description,
            "data": data or {},
        }
        self.workflow_events.append(event)
        logger.info(f"[WORKFLOW] {event_type}: {description}")

    def save_summary(self):
        """Save summary of all calls."""
        summary_file = self.log_dir / "llm_calls_summary.json"
        summary_file.write_text(json.dumps(self.calls, indent=2))
        workflow_file = self.log_dir / "workflow_events.json"
        workflow_file.write_text(json.dumps(self.workflow_events, indent=2))


class LoggingLLMClientWrapper:
    """Wrapper around LLM client that logs all calls."""

    def __init__(self, client, call_logger: LLMCallLogger, stage_name: str = "unknown"):
        self._client = client
        self._logger = call_logger
        self._stage_name = stage_name

    def complete(self, prompt: str, system_prompt: str = "", **kwargs):
        full_prompt = (
            f"SYSTEM: {system_prompt}\n\nUSER: {prompt}" if system_prompt else prompt
        )
        response = self._client.complete(
            prompt=prompt, system_prompt=system_prompt, **kwargs
        )
        self._logger.log_call(
            stage=self._stage_name,
            prompt=full_prompt,
            response=response if response else "",
            metadata=kwargs,
        )
        return response

    @property
    def client(self):
        raw_client = getattr(self._client, "client", self._client)
        return VisionClientWrapper(raw_client, self._logger)

    def __getattr__(self, name):
        return getattr(self._client, name)


class VisionClientWrapper:
    """Wrapper for OpenAI client to log vision API calls."""

    def __init__(self, client, call_logger: LLMCallLogger):
        self._client = client
        self._logger = call_logger

    @property
    def chat(self):
        return ChatWrapper(self._client.chat, self._logger)

    def __getattr__(self, name):
        return getattr(self._client, name)


class ChatWrapper:
    def __init__(self, chat_api, call_logger: LLMCallLogger):
        self._chat = chat_api
        self._logger = call_logger

    @property
    def completions(self):
        return CompletionsWrapper(self._chat.completions, self._logger)

    def __getattr__(self, name):
        return getattr(self._chat, name)


class CompletionsWrapper:
    def __init__(self, completions_api, call_logger: LLMCallLogger):
        self._completions = completions_api
        self._logger = call_logger

    def create(self, messages, **kwargs):
        prompt_summary = self._summarize_messages(messages)
        response = self._completions.create(messages=messages, **kwargs)
        response_text = response.choices[0].message.content if response.choices else ""
        self._logger.log_call(
            stage="vision_evaluation",
            prompt=prompt_summary,
            response=response_text,
            metadata={
                "model": kwargs.get("model"),
                "image_count": self._count_images(messages),
            },
        )
        return response

    def _summarize_messages(self, messages):
        summary = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [
                    c.get("text", "") for c in content if c.get("type") == "text"
                ]
                img_count = sum(1 for c in content if c.get("type") == "image_url")
                summary.append(
                    f"{role}: {' '.join(text_parts)[:500]}... [{img_count} images]"
                )
            else:
                summary.append(f"{role}: {content[:500]}")
        return "\n".join(summary)

    def _count_images(self, messages):
        count = 0
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                count += sum(1 for c in content if c.get("type") == "image_url")
        return count

    def __getattr__(self, name):
        return getattr(self._completions, name)


def main():
    """Test bracket with ribs - prone to disconnection bug."""

    # Intent that should trigger rib placement on a plate
    # This is the scenario that caused disconnected geometry before
    intent = (
        "Create a flat rectangular mounting bracket plate 120mm x 80mm x 4mm thick. "
        "Add 4 mounting holes (6.6mm diameter) at corners offset 30mm from edges. "
        "Add 2 reinforcement ribs on top, running along the length (70mm long, 4mm thick, 20mm tall). "
        "Position ribs at Y=25mm and Y=55mm from the front edge. "
        "All geometry must be a single connected solid."
    )

    # Create timestamped run directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path("data/artifacts/runs") / f"bracket_disconnection_test_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir = run_dir / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    logger.info("=" * 80)
    logger.info("DISCONNECTION BUG TEST")
    logger.info("=" * 80)
    logger.info(f"Output directory: {run_dir}")
    logger.info(f"Intent: {intent}")
    logger.info("=" * 80)

    # Setup logging
    llm_logger = LLMCallLogger(logs_dir)
    llm_logger.log_workflow_event(
        "TEST_START",
        "Starting disconnection bug test",
        {"intent": intent, "timestamp": timestamp},
    )

    # Setup pipeline
    router = LLMRouter(default_backend="openai")
    base_llm_client = router.get_client()
    llm_client = LoggingLLMClientWrapper(base_llm_client, llm_logger, "code_generation")

    embedding_client = OpenAIEmbeddingClient()
    api_catalog = CadQueryAPICatalog()

    gateway = ToolGateway()
    backend = SubprocessCadQueryBackend()
    gateway.register("cadquery", backend)

    # Vision config - key for detecting disconnection
    vision_config = VisionEvaluationConfig(
        enabled=True,
        vision_model="gpt-5.2",
        max_iterations=3,  # Give it multiple chances to fix
        confidence_threshold=0.7,
        regenerate_on_fail=True,
    )

    config = PipelineConfig(
        max_feedback_iterations=3,
        retrieval_top_k=5,
        vision_evaluation=vision_config,
    )

    pipeline = IntentToCADPipeline(
        llm_client=llm_client,
        api_catalog=api_catalog,
        embedding_client=embedding_client,
        config=config,
        gateway=gateway,
    )

    llm_logger.log_workflow_event(
        "PIPELINE_RUN_START",
        "Starting pipeline - watching for disconnection issues",
        {"max_vision_iterations": vision_config.max_iterations},
    )

    result = pipeline.run(intent=intent)

    llm_logger.log_workflow_event(
        "PIPELINE_COMPLETE",
        "Pipeline finished",
        {
            "success": result.success,
            "confidence": result.confidence,
            "duration_ms": result.total_duration_ms,
        },
    )

    # Results summary
    logger.info("=" * 80)
    logger.info("RESULTS")
    logger.info("=" * 80)
    logger.info(f"Success: {result.success}")
    logger.info(f"Confidence: {result.confidence:.2f}")
    logger.info(f"Duration: {result.total_duration_ms:.0f}ms")

    # Check geometry properties for disconnection indicators
    geom_props = result.geometry_properties
    if geom_props:
        logger.info(f"Volume: {geom_props.get('volume', 'N/A')}")
        logger.info(f"Faces: {geom_props.get('face_count', 'N/A')}")
        logger.info(f"Solids: {geom_props.get('solid_count', 'N/A')}")

        # Key check: solid_count > 1 means disconnected!
        solid_count = geom_props.get("solid_count", 1)
        if solid_count > 1:
            logger.warning(f"⚠️  DISCONNECTED GEOMETRY DETECTED: {solid_count} solids!")
            llm_logger.log_workflow_event(
                "DISCONNECTION_DETECTED",
                f"Final geometry has {solid_count} disconnected solids",
                {"solid_count": solid_count},
            )
        else:
            logger.info("✓ Geometry is a single connected solid")

    # Move generated files
    import shutil

    default_screenshots = Path("data/artifacts/screenshots")
    default_artifacts = Path("data/artifacts")

    # Move STEP files
    step_files = list(default_artifacts.glob("*bracket*.step")) + list(
        default_artifacts.glob("*mounting*.step")
    )
    for step in step_files:
        dest = run_dir / step.name
        shutil.move(str(step), str(dest))
        logger.info(f"✓ Moved STEP: {dest.name}")

    # Move screenshots
    if default_screenshots.exists():
        pngs = list(default_screenshots.glob("*bracket*.png")) + list(
            default_screenshots.glob("*mounting*.png")
        )
        for png in pngs:
            dest = screenshots_dir / png.name
            shutil.move(str(png), str(dest))

    # Save metadata
    metadata = {
        "test": "disconnection_bug",
        "timestamp": timestamp,
        "intent": intent,
        "success": result.success,
        "confidence": result.confidence,
        "duration_ms": result.total_duration_ms,
        "geometry_properties": geom_props,
        "disconnection_detected": (
            geom_props.get("solid_count", 1) > 1 if geom_props else False
        ),
    }

    metadata_file = run_dir / "test_results.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    # Save final code for inspection
    if result.final_code:
        code_file = run_dir / "final_code.py"
        code_file.write_text(result.final_code)
        logger.info(f"✓ Saved final code: {code_file}")

    llm_logger.save_summary()

    logger.info(f"\n📁 All files saved to: {run_dir}")
    logger.info(f"📊 Total LLM calls: {llm_logger.call_count}")


if __name__ == "__main__":
    main()
