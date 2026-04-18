"""Tests for ops_program JSON strict enforcement and repair (14-04).

TDD RED phase: Tests for JSON repair and strict generation.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.agents.ops_generator import (
    ArtifactGenerationError,
    OpsGeneratorAgent,
    repair_json,
)


class TestRepairJson:
    """Tests for repair_json helper function."""

    def test_valid_json_passthrough(self):
        """Valid JSON passes through unchanged."""
        valid = '{"name": "part", "operations": []}'
        result = repair_json(valid)
        assert result == json.loads(valid)

    def test_trailing_comma_repair(self):
        """Trailing comma in object gets repaired."""
        malformed = '{"name": "part", "value": 10,}'
        result = repair_json(malformed)
        assert result["name"] == "part"
        assert result["value"] == 10

    def test_trailing_comma_array_repair(self):
        """Trailing comma in array gets repaired."""
        malformed = '{"items": [1, 2, 3,]}'
        result = repair_json(malformed)
        assert result["items"] == [1, 2, 3]

    def test_single_line_comment_repair(self):
        """Single-line JS comments get stripped."""
        malformed = """{
            "name": "part", // this is a comment
            "value": 10
        }"""
        result = repair_json(malformed)
        assert result["name"] == "part"
        assert result["value"] == 10

    def test_multi_line_comment_repair(self):
        """Multi-line comments get stripped."""
        malformed = """{
            "name": "part",
            /* this is a
               multi-line comment */
            "value": 10
        }"""
        result = repair_json(malformed)
        assert result["name"] == "part"
        assert result["value"] == 10

    def test_unquoted_keys_repair(self):
        """Unquoted keys get fixed (json5 feature)."""
        malformed = '{name: "part", value: 10}'
        result = repair_json(malformed)
        assert result["name"] == "part"
        assert result["value"] == 10

    def test_single_quotes_repair(self):
        """Single quotes get converted to double quotes."""
        malformed = "{'name': 'part', 'value': 10}"
        result = repair_json(malformed)
        assert result["name"] == "part"
        assert result["value"] == 10

    def test_total_garbage_raises(self):
        """Total garbage raises ValueError."""
        garbage = "This is not JSON at all, just text."
        with pytest.raises(ValueError, match="repair failed"):
            repair_json(garbage)


class TestStrictJsonGeneration:
    """Tests for strict JSON generation with response_format."""

    @pytest.fixture
    def mock_engine(self):
        """Create mock hypergraph engine."""
        engine = MagicMock()
        engine.get_nodes_by_type.return_value = []
        return engine

    @pytest.fixture
    def mock_llm_client(self):
        """Create mock LLM client that simulates OpenAI API."""
        return MagicMock()

    def test_response_format_json_object_used(self, mock_engine, mock_llm_client):
        """response_format=json_object is always set for ops_program gen."""
        # Setup mock to return valid JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "schema_version": "ops_program.v1",
                "name": "test_part",
                "operations": [],
            }
        )
        mock_llm_client.chat.completions.create.return_value = mock_response

        agent = OpsGeneratorAgent(
            engine=mock_engine,
            llm=mock_llm_client,
            validate_geometry=False,
        )

        result, error = agent.generate_from_specs(
            specs=[MagicMock(description="test spec")],
            contracts=[],
        )

        # Verify response_format was passed
        call_args = mock_llm_client.chat.completions.create.call_args
        assert "response_format" in call_args.kwargs
        assert call_args.kwargs["response_format"] == {"type": "json_object"}

    def test_repair_on_malformed_json(self, mock_engine, mock_llm_client):
        """Malformed JSON triggers repair before failure."""
        # First call returns JSON with trailing comma
        malformed_response = MagicMock()
        malformed_response.choices = [MagicMock()]
        malformed_response.choices[0].message.content = '{"name": "part", "ops": [],}'
        mock_llm_client.chat.completions.create.return_value = malformed_response

        agent = OpsGeneratorAgent(
            engine=mock_engine,
            llm=mock_llm_client,
            validate_geometry=False,
        )

        result, error = agent.generate_from_specs(
            specs=[MagicMock(description="test")],
            contracts=[],
        )

        # Should succeed via repair
        assert error is None
        assert result is not None
        assert result["name"] == "part"

    def test_retry_on_total_failure(self, mock_engine, mock_llm_client):
        """Total garbage triggers retry with stricter prompt (strict method)."""
        # First call returns garbage, second returns valid JSON
        garbage_response = MagicMock()
        garbage_response.choices = [MagicMock()]
        garbage_response.choices[0].message.content = (
            "Here is your design:\n\nThe bracket..."
        )

        valid_response = MagicMock()
        valid_response.choices = [MagicMock()]
        valid_response.choices[0].message.content = '{"name": "part", "operations": []}'

        mock_llm_client.chat.completions.create.side_effect = [
            garbage_response,
            valid_response,
        ]

        agent = OpsGeneratorAgent(
            engine=mock_engine,
            llm=mock_llm_client,
            validate_geometry=False,
        )

        # Use generate_from_specs_strict which has retry logic
        result = agent.generate_from_specs_strict(
            specs=[MagicMock(description="test")],
            contracts=[],
        )

        # Should succeed on retry
        assert result is not None
        assert result["name"] == "part"
        # Verify retry happened (2 calls total)
        assert mock_llm_client.chat.completions.create.call_count == 2

    def test_max_retries_then_error(self, mock_engine, mock_llm_client):
        """After max retries, raises ArtifactGenerationError."""
        # All calls return garbage
        garbage_response = MagicMock()
        garbage_response.choices = [MagicMock()]
        garbage_response.choices[0].message.content = "Not JSON at all"
        mock_llm_client.chat.completions.create.return_value = garbage_response

        agent = OpsGeneratorAgent(
            engine=mock_engine,
            llm=mock_llm_client,
            validate_geometry=False,
        )

        with pytest.raises(ArtifactGenerationError, match="max retries"):
            agent.generate_from_specs_strict(
                specs=[MagicMock(description="test")],
                contracts=[],
            )

    def test_extracts_json_from_markdown(self, mock_engine, mock_llm_client):
        """JSON wrapped in markdown code blocks gets extracted."""
        markdown_response = MagicMock()
        markdown_response.choices = [MagicMock()]
        markdown_response.choices[0].message.content = """Here's the design:

```json
{
  "name": "bracket",
  "operations": []
}
```

This design meets all requirements."""
        mock_llm_client.chat.completions.create.return_value = markdown_response

        agent = OpsGeneratorAgent(
            engine=mock_engine,
            llm=mock_llm_client,
            validate_geometry=False,
        )

        result, error = agent.generate_from_specs(
            specs=[MagicMock(description="test")],
            contracts=[],
        )

        assert error is None
        assert result["name"] == "bracket"


class TestArtifactGenerationError:
    """Tests for custom exception."""

    def test_exception_message(self):
        """Exception includes descriptive message."""
        error = ArtifactGenerationError("Failed after 3 retries: invalid JSON")
        assert "3 retries" in str(error)
        assert "invalid JSON" in str(error)

    def test_exception_inherits_from_value_error(self):
        """Exception inherits from ValueError for compatibility."""
        error = ArtifactGenerationError("test")
        assert isinstance(error, ValueError)
