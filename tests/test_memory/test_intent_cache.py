"""Tests for IntentCache."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Env var for opt-in integration tests
RUN_INTEGRATION = os.environ.get("RUN_INTEGRATION_TESTS", "0") == "1"


def _create_mock_hypergraph(path: Path) -> None:
    """Create a minimal hypergraph JSON for testing."""
    data = {
        "nodes": {
            "goal_1": {
                "id": "goal_1",
                "node_type": "goal",
                "description": "Test goal",
                "confidence": 1.0,
                "metadata": {},
            }
        },
        "edges": {},
        "metadata": {"saved_at": "2024-01-01T00:00:00"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class TestStepType:
    """Tests for StepType enum."""

    def test_step_types_exist(self):
        from src.memory import StepType

        assert StepType.GRS == "grs"
        assert StepType.CONTRACTS == "contracts"
        assert StepType.FULL_PIPELINE == "full_pipeline"


class TestCacheHit:
    """Tests for CacheHit dataclass."""

    def test_cache_hit_fields(self):
        from src.memory import CacheHit, StepType

        hit = CacheHit(
            original_intent="Design a bracket",
            step_type=StepType.GRS,
            score=0.95,
            hypergraph_path=Path("/tmp/test.json"),
            metadata={"key": "value"},
            cached_at="2024-01-01T00:00:00",
        )

        assert hit.original_intent == "Design a bracket"
        assert hit.step_type == StepType.GRS
        assert hit.score == 0.95
        assert hit.hypergraph_path == Path("/tmp/test.json")
        assert hit.cached_at == "2024-01-01T00:00:00"


class TestRestoreFromCache:
    """Tests for restore_from_cache function."""

    def test_restore_copies_file(self, tmp_path):
        from src.memory import CacheHit, StepType, restore_from_cache

        # Create source file
        source = tmp_path / "source" / "hypergraph.json"
        _create_mock_hypergraph(source)

        hit = CacheHit(
            original_intent="Test",
            step_type=StepType.FULL_PIPELINE,
            score=0.9,
            hypergraph_path=source,
            metadata={},
            cached_at="2024-01-01",
        )

        # Restore to new location
        target = tmp_path / "target" / "restored.json"
        restore_from_cache(hit, target)

        assert target.exists()
        assert json.loads(target.read_text()) == json.loads(source.read_text())


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_INTEGRATION_TESTS=1 to run (requires OpenAI API key)",
)
class TestIntentCacheIntegration:
    """Integration tests for IntentCache (requires API key)."""

    def test_store_and_search(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path / "memory", threshold=0.85)

        # Create test hypergraph
        hg_path = tmp_path / "hypergraph.json"
        _create_mock_hypergraph(hg_path)

        # Store
        cache_id = cache.store(
            intent="Design a mounting bracket for a 5kg load",
            step_type=StepType.FULL_PIPELINE,
            hypergraph_path=hg_path,
            metadata={"test": True},
        )

        assert cache_id is not None

        # Search for similar intent
        hit = cache.search(
            "Create a bracket that holds 5 kilograms",
            StepType.FULL_PIPELINE,
        )

        assert hit is not None
        assert hit.score >= 0.85

    def test_no_match_below_threshold(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path / "memory", threshold=0.99)

        # Create and store
        hg_path = tmp_path / "hypergraph.json"
        _create_mock_hypergraph(hg_path)

        cache.store(
            intent="Design a mounting bracket",
            step_type=StepType.FULL_PIPELINE,
            hypergraph_path=hg_path,
        )

        # Search for very different intent
        hit = cache.search(
            "Build a rocket engine",
            StepType.FULL_PIPELINE,
        )

        assert hit is None

    def test_clear_cache(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path / "memory")

        # Store entry
        hg_path = tmp_path / "hypergraph.json"
        _create_mock_hypergraph(hg_path)

        cache.store(
            intent="Test intent",
            step_type=StepType.GRS,
            hypergraph_path=hg_path,
        )

        # Clear
        cache.clear()

        # Stats should show 0 entries
        stats = cache.get_stats()
        assert stats["entries"] == 0


class TestIntentCacheUnit:
    """Unit tests that don't require API."""

    def test_cache_dir_creation(self, tmp_path):
        from src.memory import IntentCache

        memory_path = tmp_path / "new_memory"
        cache = IntentCache(memory_path=memory_path)

        assert cache.cache_dir.exists()
        assert cache.cache_dir == memory_path / "cache"

    def test_default_threshold(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path)
        # Default from config is 0.85
        assert cache.threshold == 0.85

    def test_custom_threshold(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, threshold=0.90)
        assert cache.threshold == 0.90

    def test_generate_cache_id_unique(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)

        id1 = cache._generate_cache_id("intent1", StepType.GRS)
        id2 = cache._generate_cache_id("intent2", StepType.GRS)

        assert id1 != id2
        assert len(id1) == 16
        assert len(id2) == 16

    def test_stats_empty_cache(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path)
        stats = cache.get_stats()

        assert stats["entries"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["threshold"] == 0.85


class TestScoreToSimilarity:
    """Unit tests for _score_to_similarity()."""

    def test_none_input_returns_none(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="distance")
        assert cache._score_to_similarity(None) is None

    def test_invalid_type_returns_none(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path)
        assert cache._score_to_similarity("invalid") is None
        assert cache._score_to_similarity([1, 2]) is None

    def test_distance_mode_converts(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="distance")
        # distance=0 -> similarity=1.0
        assert cache._score_to_similarity(0.0) == 1.0
        # distance=1 -> similarity=0.5
        assert cache._score_to_similarity(1.0) == 0.5
        # distance=3 -> similarity=0.25
        assert cache._score_to_similarity(3.0) == 0.25

    def test_similarity_mode_passthrough(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="similarity")
        assert cache._score_to_similarity(0.9) == 0.9
        assert cache._score_to_similarity(0.5) == 0.5

    def test_auto_mode_detects_similarity(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="auto", threshold=0.85)
        # Values in [0,1] with threshold in [0,1] -> treat as similarity
        assert cache._score_to_similarity(0.9) == 0.9

    def test_auto_mode_detects_distance(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="auto", threshold=0.85)
        # Values > 1 -> treat as distance
        assert cache._score_to_similarity(3.0) == 0.25

    def test_clamps_to_0_1(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="similarity")
        assert cache._score_to_similarity(-0.5) == 0.0
        assert cache._score_to_similarity(1.5) == 1.0

    def test_unknown_mode_defaults_to_distance(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="bogus")
        assert cache.score_mode == "distance"


class TestSearchMocked:
    """Mock tests for search() without API calls."""

    def test_search_returns_none_on_empty_results(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        mock_memory.search.return_value = {"results": []}
        cache._memory = mock_memory

        result = cache.search("test intent", StepType.GRS)
        assert result is None

    def test_search_returns_none_below_threshold(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(
            memory_path=tmp_path, threshold=0.9, score_mode="similarity"
        )
        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [
                {
                    "score": 0.5,
                    "metadata": {"step_type": "grs", "cache_id": "abc123"},
                }
            ]
        }
        cache._memory = mock_memory

        result = cache.search("test", StepType.GRS)
        assert result is None

    def test_search_returns_hit_above_threshold(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(
            memory_path=tmp_path, threshold=0.8, score_mode="similarity"
        )

        # Create cache file
        cache_file = cache.cache_dir / "abc123.json"
        _create_mock_hypergraph(cache_file)

        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [
                {
                    "score": 0.95,
                    "metadata": {
                        "step_type": "grs",
                        "cache_id": "abc123",
                        "intent": "original intent",
                        "cached_at": "2024-01-01",
                    },
                }
            ]
        }
        cache._memory = mock_memory

        hit = cache.search("test", StepType.GRS)
        assert hit is not None
        assert hit.score == 0.95
        assert hit.original_intent == "original intent"

    def test_search_returns_none_if_cache_file_missing(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(
            memory_path=tmp_path, threshold=0.5, score_mode="similarity"
        )
        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [
                {
                    "score": 0.9,
                    "metadata": {"step_type": "grs", "cache_id": "nonexistent"},
                }
            ]
        }
        cache._memory = mock_memory

        result = cache.search("test", StepType.GRS)
        assert result is None

    def test_search_gracefully_handles_exception(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        mock_memory.search.side_effect = RuntimeError("API down")
        cache._memory = mock_memory

        result = cache.search("test", StepType.GRS)
        assert result is None  # Graceful degradation

    def test_search_filters_by_step_type(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(
            memory_path=tmp_path, threshold=0.5, score_mode="similarity"
        )

        cache_file = cache.cache_dir / "grs123.json"
        _create_mock_hypergraph(cache_file)

        mock_memory = MagicMock()
        mock_memory.search.return_value = {
            "results": [
                # Wrong step_type - should be filtered
                {
                    "score": 0.99,
                    "metadata": {"step_type": "contracts", "cache_id": "x"},
                },
                # Correct step_type
                {"score": 0.8, "metadata": {"step_type": "grs", "cache_id": "grs123"}},
            ]
        }
        cache._memory = mock_memory

        hit = cache.search("test", StepType.GRS)
        assert hit is not None
        assert hit.step_type == StepType.GRS


class TestStoreMocked:
    """Mock tests for store() without API calls."""

    def test_store_copies_hypergraph(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        cache._memory = mock_memory

        hg_path = tmp_path / "source.json"
        _create_mock_hypergraph(hg_path)

        cache_id = cache.store("test intent", StepType.GRS, hg_path)

        cache_file = cache.cache_dir / f"{cache_id}.json"
        assert cache_file.exists()
        mock_memory.add.assert_called_once()

    def test_store_raises_on_missing_file(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        cache._memory = mock_memory

        with pytest.raises(FileNotFoundError):
            cache.store("test", StepType.GRS, tmp_path / "nonexistent.json")

    def test_store_cleans_up_on_mem0_error(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        mock_memory.add.side_effect = RuntimeError("mem0 error")
        cache._memory = mock_memory

        hg_path = tmp_path / "source.json"
        _create_mock_hypergraph(hg_path)

        with pytest.raises(RuntimeError):
            cache.store("test", StepType.GRS, hg_path)

        # Should clean up partial cache file
        cache_files = list(cache.cache_dir.glob("*.json"))
        assert len(cache_files) == 0

    def test_store_includes_metadata(self, tmp_path):
        from src.memory import IntentCache, StepType

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        cache._memory = mock_memory

        hg_path = tmp_path / "source.json"
        _create_mock_hypergraph(hg_path)

        cache.store("test intent", StepType.GRS, hg_path, metadata={"auto": True})

        call_kwargs = mock_memory.add.call_args[1]
        assert call_kwargs["metadata"]["intent"] == "test intent"
        assert call_kwargs["metadata"]["step_type"] == "grs"
        assert call_kwargs["metadata"]["auto"] is True


class TestErrorPaths:
    """Test error handling paths."""

    def test_coerce_invalid_score_mode(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path, score_mode="invalid_mode")
        assert cache.score_mode == "distance"

    def test_search_handles_list_response(self, tmp_path):
        """mem0 may return list instead of dict."""
        from src.memory import IntentCache, StepType

        cache = IntentCache(
            memory_path=tmp_path, threshold=0.5, score_mode="similarity"
        )

        cache_file = cache.cache_dir / "abc.json"
        _create_mock_hypergraph(cache_file)

        mock_memory = MagicMock()
        # Return list directly instead of {"results": [...]}
        mock_memory.search.return_value = [
            {"score": 0.9, "metadata": {"step_type": "grs", "cache_id": "abc"}}
        ]
        cache._memory = mock_memory

        hit = cache.search("test", StepType.GRS)
        assert hit is not None

    def test_list_entries_handles_exception(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        mock_memory.get_all.side_effect = RuntimeError("fail")
        cache._memory = mock_memory

        entries = cache.list_entries()
        assert entries == []

    def test_clear_handles_delete_all_exception(self, tmp_path):
        from src.memory import IntentCache

        cache = IntentCache(memory_path=tmp_path)
        mock_memory = MagicMock()
        mock_memory.delete_all.side_effect = RuntimeError("fail")
        cache._memory = mock_memory

        # Create a cache file
        cache_file = cache.cache_dir / "test.json"
        _create_mock_hypergraph(cache_file)

        # Should not raise, should still clear local files
        count = cache.clear()
        assert count == 1
        assert not cache_file.exists()


# Golden test set for threshold validation
GOLDEN_SIMILAR_PAIRS = [
    # (intent_a, intent_b, expected_similar)
    (
        "Design a mounting bracket for 5kg load",
        "Create a bracket holding 5 kilograms",
        True,
    ),
    ("Design a gear with 20 teeth", "Create a 20-tooth gear", True),
    (
        "Build a heat sink for 50W CPU",
        "Design cooling solution for 50 watt processor",
        True,
    ),
    ("Create a shaft 10mm diameter", "Design 10mm shaft", True),
]

GOLDEN_DISSIMILAR_PAIRS = [
    ("Design a mounting bracket for 5kg", "Build a rocket engine", False),
    ("Create a plastic enclosure", "Design a metal gear assembly", False),
    ("Design a PCB for LED driver", "Create a mechanical linkage", False),
    ("Build a water pump housing", "Design an aircraft wing", False),
]


@pytest.mark.skipif(
    not RUN_INTEGRATION,
    reason="Set RUN_INTEGRATION_TESTS=1 to run golden tests",
)
class TestGoldenIntentPairs:
    """Golden test set to validate similarity threshold (0.85)."""

    @pytest.fixture
    def cache(self, tmp_path):
        from src.memory import IntentCache

        return IntentCache(memory_path=tmp_path / "memory", threshold=0.85)

    @pytest.mark.parametrize("intent_a,intent_b,expected", GOLDEN_SIMILAR_PAIRS)
    def test_similar_intents_match(self, cache, tmp_path, intent_a, intent_b, expected):
        from src.memory import StepType

        hg_path = tmp_path / "hg.json"
        _create_mock_hypergraph(hg_path)

        cache.store(intent_a, StepType.FULL_PIPELINE, hg_path)
        hit = cache.search(intent_b, StepType.FULL_PIPELINE)

        if expected:
            assert hit is not None, f"Expected match: '{intent_a}' ~ '{intent_b}'"
            assert hit.score >= 0.85
        else:
            assert hit is None

    @pytest.mark.parametrize("intent_a,intent_b,expected", GOLDEN_DISSIMILAR_PAIRS)
    def test_dissimilar_intents_no_match(
        self, cache, tmp_path, intent_a, intent_b, expected
    ):
        from src.memory import StepType

        hg_path = tmp_path / "hg.json"
        _create_mock_hypergraph(hg_path)

        cache.store(intent_a, StepType.FULL_PIPELINE, hg_path)
        hit = cache.search(intent_b, StepType.FULL_PIPELINE)

        assert hit is None, f"Unexpected match: '{intent_a}' ~ '{intent_b}'"
