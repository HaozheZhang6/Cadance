"""Tests for LLM abstraction layer."""

import pytest

from src.cad.intent_decomposition.llm import (
    BaseLLMClient,
    LLMClient,
    LLMConfig,
    LLMProvider,
    LLMRouter,
    MockLLMClient,
)


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self):
        """Provider enum should have expected values."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.MOCK.value == "mock"


class TestLLMConfig:
    """Tests for LLMConfig dataclass."""

    def test_default_config(self):
        """Config should have sensible defaults."""
        config = LLMConfig()
        assert config.temperature == 0.7
        assert config.max_tokens == 2000
        assert config.timeout == 60.0

    def test_custom_config(self):
        """Config should accept custom values."""
        config = LLMConfig(temperature=0.5, max_tokens=1000, timeout=30.0)
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.timeout == 30.0


class TestMockLLMClient:
    """Tests for MockLLMClient (from src/agents/llm)."""

    @pytest.fixture
    def client(self):
        """Create mock client."""
        return MockLLMClient(default_response="test response")

    def test_client_creation(self, client):
        """Client should be creatable."""
        assert client is not None

    def test_is_configured(self, client):
        """Mock should always be configured."""
        assert client.is_configured() is True

    def test_complete_returns_default(self, client):
        """Complete should return default response."""
        response = client.complete("test prompt")
        assert response == "test response"

    def test_complete_records_prompt(self, client):
        """Complete should record last prompt."""
        client.complete("my prompt")
        assert client.last_prompt == "my prompt"

    def test_complete_increments_call_count(self, client):
        """Complete should track call count."""
        assert client.call_count == 0
        client.complete("a")
        assert client.call_count == 1
        client.complete("b")
        assert client.call_count == 2

    def test_complete_json_parses_json(self):
        """Complete JSON should parse valid JSON responses."""
        client = MockLLMClient(default_response='{"key": "value"}')
        result = client.complete_json("prompt")
        assert result == {"key": "value"}

    def test_complete_json_returns_empty_on_invalid(self):
        """Complete JSON should return empty dict for invalid JSON."""
        client = MockLLMClient(default_response="not json")
        result = client.complete_json("prompt")
        assert result == {}


class TestLLMClient:
    """Tests for LLMClient (from src/agents/llm)."""

    def test_client_creation_with_key(self):
        """Client with API key should be configured."""
        client = LLMClient(api_key="test-key-123")
        assert client.is_configured() is True

    def test_complete_raises_without_key(self):
        """Complete should raise when not configured."""
        # Create client that explicitly has no key
        client = LLMClient.__new__(LLMClient)
        client.client = None
        client.api_key = None
        client.model = "gpt-4o"

        with pytest.raises(RuntimeError, match="No OpenAI API key"):
            client.complete("test")


class TestLLMRouter:
    """Tests for LLMRouter."""

    def test_router_creation(self):
        """Router should be creatable."""
        router = LLMRouter(default_backend="mock")
        assert router is not None

    def test_router_invalid_backend_raises(self):
        """Router should raise for invalid backend."""
        with pytest.raises(ValueError, match="Unknown backend"):
            LLMRouter(default_backend="invalid")

    def test_available_backends(self):
        """Router should list available backends."""
        router = LLMRouter(default_backend="mock")
        backends = router.available_backends()
        assert "mock" in backends
        assert "openai" in backends

    def test_get_client_mock(self):
        """Router should return mock client."""
        router = LLMRouter(default_backend="mock")
        client = router.get_client()
        assert isinstance(client, MockLLMClient)

    def test_get_client_caches(self):
        """Router should cache clients."""
        router = LLMRouter(default_backend="mock")
        client1 = router.get_client()
        client2 = router.get_client()
        assert client1 is client2

    def test_get_client_explicit_backend(self):
        """Router should allow explicit backend selection."""
        router = LLMRouter(default_backend="openai")
        client = router.get_client("mock")
        assert isinstance(client, MockLLMClient)

    def test_is_backend_configured_mock(self):
        """Mock backend should be configured."""
        router = LLMRouter(default_backend="mock")
        assert router.is_backend_configured("mock") is True

    def test_complete_delegates(self):
        """Router complete should delegate to client."""
        router = LLMRouter(default_backend="mock")
        response = router.complete("test", backend="mock")
        assert response == "Mock response"

    def test_complete_json_delegates(self):
        """Router complete_json should delegate to client."""
        router = LLMRouter(default_backend="mock")
        # Mock returns empty dict for non-JSON responses
        response = router.complete_json("test", backend="mock")
        assert response == {}

    def test_register_backend(self):
        """Router should allow registering new backends."""

        class CustomClient:
            pass

        LLMRouter.register_backend("custom", CustomClient)
        assert "custom" in LLMRouter._backends

        # Clean up
        del LLMRouter._backends["custom"]


class TestBaseLLMClientProtocol:
    """Tests for BaseLLMClient protocol compliance."""

    def test_mock_implements_protocol(self):
        """MockLLMClient should implement BaseLLMClient."""
        client = MockLLMClient()
        assert isinstance(client, BaseLLMClient)

    def test_llm_client_implements_protocol(self):
        """LLMClient should implement BaseLLMClient."""
        client = LLMClient(api_key="test-key")
        assert isinstance(client, BaseLLMClient)
