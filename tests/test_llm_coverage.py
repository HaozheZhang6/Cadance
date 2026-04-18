"""Tests for LLM client coverage - error handling and edge cases."""

from unittest.mock import MagicMock, patch

import pytest

from src.agents.llm import LLMClient, MockLLMClient


class TestLLMClientInitialization:
    """Tests for LLMClient initialization."""

    def test_init_without_api_key(self):
        """LLMClient without API key should set client to None."""
        with patch("src.agents.llm.OPENAI_API_KEY", None):
            client = LLMClient(api_key=None)
            assert client.client is None
            assert client.is_configured() is False

    def test_init_with_api_key(self):
        """LLMClient with API key should create OpenAI client."""
        with patch("src.agents.llm.OpenAI") as mock_openai:
            client = LLMClient(api_key="test-key")
            mock_openai.assert_called_once_with(api_key="test-key")
            assert client.is_configured() is True

    def test_init_uses_env_vars(self):
        """LLMClient should use environment variables."""
        with patch("src.agents.llm.OPENAI_API_KEY", "env-key"):
            with patch("src.agents.llm.OPENAI_MODEL", "gpt-5.2"):
                with patch("src.agents.llm.OpenAI"):
                    client = LLMClient()
                    assert client.api_key == "env-key"
                    assert client.model == "gpt-5.2"


class TestLLMClientComplete:
    """Tests for LLMClient.complete() method."""

    def test_complete_without_client_raises(self):
        """complete() should raise RuntimeError if no client configured."""
        with patch("src.agents.llm.OPENAI_API_KEY", None):
            client = LLMClient(api_key=None)
            with pytest.raises(RuntimeError, match="No OpenAI API key configured"):
                client.complete("test prompt")

    def test_complete_with_system_prompt(self):
        """complete() should include system prompt in messages."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.total_tokens = 100

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            client.complete("user prompt", system_prompt="system prompt")

            call_args = mock_openai.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == "system prompt"
            assert messages[1]["role"] == "user"

    def test_complete_without_system_prompt(self):
        """complete() should work without system prompt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage.total_tokens = 50

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            client.complete("user prompt")

            call_args = mock_openai.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"

    def test_complete_handles_none_content(self):
        """complete() should handle None content in response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage.total_tokens = 10

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            result = client.complete("prompt")
            assert result == ""

    def test_complete_handles_none_usage(self):
        """complete() should handle None usage in response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "response"
        mock_response.usage = None

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            result = client.complete("prompt")
            assert result == "response"


class TestLLMClientCompleteJson:
    """Tests for LLMClient.complete_json() method."""

    def test_complete_json_without_client_raises(self):
        """complete_json() should raise RuntimeError if no client configured."""
        with patch("src.agents.llm.OPENAI_API_KEY", None):
            client = LLMClient(api_key=None)
            with pytest.raises(RuntimeError, match="No OpenAI API key configured"):
                client.complete_json("test prompt")

    def test_complete_json_with_schema(self):
        """complete_json() should use structured output with schema."""
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str
            value: int

        mock_parsed = TestSchema(name="test", value=42)
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = mock_parsed

        mock_openai = MagicMock()
        mock_openai.beta.chat.completions.parse.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            result = client.complete_json("prompt", schema=TestSchema)

            assert result == {"name": "test", "value": 42}
            mock_openai.beta.chat.completions.parse.assert_called_once()

    def test_complete_json_with_schema_parse_failure(self):
        """complete_json() should raise ValueError on parse failure."""
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.parsed = None

        mock_openai = MagicMock()
        mock_openai.beta.chat.completions.parse.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            with pytest.raises(ValueError, match="Failed to parse structured response"):
                client.complete_json("prompt", schema=TestSchema)

    def test_complete_json_without_schema_json_mode(self):
        """complete_json() without schema should use JSON mode."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            result = client.complete_json("prompt")

            assert result == {"key": "value"}
            call_args = mock_openai.chat.completions.create.call_args
            assert call_args.kwargs["response_format"] == {"type": "json_object"}

    def test_complete_json_with_system_prompt_appends_instruction(self):
        """complete_json() should append JSON instruction to system prompt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": true}'

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            client.complete_json("prompt", system_prompt="Be helpful")

            call_args = mock_openai.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert "Respond only with valid JSON" in messages[0]["content"]
            assert "Be helpful" in messages[0]["content"]

    def test_complete_json_without_system_prompt_inserts_instruction(self):
        """complete_json() should insert JSON instruction without system prompt."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"result": true}'

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            client.complete_json("prompt")

            call_args = mock_openai.chat.completions.create.call_args
            messages = call_args.kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert "Respond only with valid JSON" in messages[0]["content"]

    def test_complete_json_strips_markdown_code_block(self):
        """complete_json() should strip markdown code blocks."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n{"key": "value"}\n```'

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            result = client.complete_json("prompt")
            assert result == {"key": "value"}

    def test_complete_json_handles_empty_response(self):
        """complete_json() should handle empty response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            result = client.complete_json("prompt")
            assert result == {}

    def test_complete_json_raises_on_invalid_json(self):
        """complete_json() should raise ValueError on invalid JSON."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not valid json"

        mock_openai = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_response

        with patch("src.agents.llm.OpenAI", return_value=mock_openai):
            client = LLMClient(api_key="test-key")
            with pytest.raises(ValueError, match="Invalid JSON response"):
                client.complete_json("prompt")


class TestMockLLMClient:
    """Tests for MockLLMClient."""

    def test_mock_client_tracks_calls(self):
        """MockLLMClient should track call count and last prompt."""
        client = MockLLMClient(default_response="test response")

        client.complete("first prompt")
        assert client.call_count == 1
        assert client.last_prompt == "first prompt"

        client.complete("second prompt")
        assert client.call_count == 2
        assert client.last_prompt == "second prompt"

    def test_mock_client_returns_default_response(self):
        """MockLLMClient should return configured default response."""
        client = MockLLMClient(default_response="my response")
        result = client.complete("any prompt")
        assert result == "my response"

    def test_mock_client_complete_json_parses_json(self):
        """MockLLMClient.complete_json() should parse JSON response."""
        client = MockLLMClient(default_response='{"key": "value"}')
        result = client.complete_json("prompt")
        assert result == {"key": "value"}

    def test_mock_client_complete_json_returns_empty_on_invalid(self):
        """MockLLMClient.complete_json() should return {} on invalid JSON."""
        client = MockLLMClient(default_response="not json")
        result = client.complete_json("prompt")
        assert result == {}

    def test_mock_client_is_always_configured(self):
        """MockLLMClient.is_configured() should always return True."""
        client = MockLLMClient()
        assert client.is_configured() is True
