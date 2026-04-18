"""Tests for web search tool."""

from src.tools.web_search import (
    TRUSTED_DOMAINS,
    SearchResult,
    SourceType,
    WebSearchTool,
)


class TestSourceType:
    """Tests for SourceType enum."""

    def test_source_types_exist(self):
        """All expected source types exist."""
        assert SourceType.AUTHORITATIVE.value == "authoritative"
        assert SourceType.VENDOR_DATASHEET.value == "vendor_datasheet"
        assert SourceType.PEER_REVIEWED.value == "peer_reviewed"
        assert SourceType.COMMUNITY.value == "community"
        assert SourceType.UNKNOWN.value == "unknown"


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """SearchResult creates with all fields."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            source_type=SourceType.COMMUNITY,
            confidence=0.5,
        )
        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.source_type == SourceType.COMMUNITY
        assert result.confidence == 0.5


class TestTrustedDomains:
    """Tests for domain classification."""

    def test_authoritative_domains(self):
        """Standards bodies classified as authoritative."""
        assert TRUSTED_DOMAINS["iso.org"] == SourceType.AUTHORITATIVE
        assert TRUSTED_DOMAINS["astm.org"] == SourceType.AUTHORITATIVE
        assert TRUSTED_DOMAINS["nist.gov"] == SourceType.AUTHORITATIVE

    def test_vendor_datasheet_domains(self):
        """Vendor sites classified as vendor_datasheet."""
        assert TRUSTED_DOMAINS["matweb.com"] == SourceType.VENDOR_DATASHEET
        assert TRUSTED_DOMAINS["ti.com"] == SourceType.VENDOR_DATASHEET
        assert TRUSTED_DOMAINS["mcmaster.com"] == SourceType.VENDOR_DATASHEET

    def test_peer_reviewed_domains(self):
        """Academic sites classified as peer_reviewed."""
        assert TRUSTED_DOMAINS["arxiv.org"] == SourceType.PEER_REVIEWED
        assert TRUSTED_DOMAINS["sciencedirect.com"] == SourceType.PEER_REVIEWED

    def test_community_domains(self):
        """Community sites classified as community."""
        assert TRUSTED_DOMAINS["stackoverflow.com"] == SourceType.COMMUNITY
        assert TRUSTED_DOMAINS["reddit.com"] == SourceType.COMMUNITY


class TestWebSearchTool:
    """Tests for WebSearchTool class."""

    def test_init_default(self):
        """Tool initializes with default backend."""
        tool = WebSearchTool()
        assert tool.api_key is None
        assert tool.backend == "mock"

    def test_init_with_api_key(self):
        """Tool initializes with API key."""
        tool = WebSearchTool(api_key="test-key", backend="serpapi")
        assert tool.api_key == "test-key"
        assert tool.backend == "serpapi"

    def test_name(self):
        """Tool name is correct."""
        tool = WebSearchTool()
        assert tool.name == "WebSearchTool"

    def test_capabilities(self):
        """Tool has correct capabilities."""
        tool = WebSearchTool()
        caps = tool.capabilities
        assert len(caps) == 1
        assert caps[0].name == "web_search"
        assert "search" in caps[0].tags

    def test_input_schema(self):
        """Input schema is valid."""
        tool = WebSearchTool()
        schema = tool.input_schema
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    def test_output_schema(self):
        """Output schema is valid."""
        tool = WebSearchTool()
        schema = tool.output_schema
        assert schema["type"] == "object"
        assert "results" in schema["properties"]

    def test_is_deterministic(self):
        """Web search is not deterministic."""
        tool = WebSearchTool()
        assert tool.is_deterministic is False

    def test_cost_estimate(self):
        """Cost estimate is moderate."""
        tool = WebSearchTool()
        assert tool.cost_estimate == 0.3

    def test_validate_inputs_valid(self):
        """Valid inputs pass validation."""
        tool = WebSearchTool()
        assert tool.validate_inputs({"query": "aluminum 6061 properties"})

    def test_validate_inputs_missing_query(self):
        """Missing query fails validation."""
        tool = WebSearchTool()
        assert not tool.validate_inputs({})

    def test_validate_inputs_wrong_type(self):
        """Wrong query type fails validation."""
        tool = WebSearchTool()
        assert not tool.validate_inputs({"query": 123})

    def test_execute_invalid_inputs(self):
        """Execute with invalid inputs returns error."""
        tool = WebSearchTool()
        result = tool.execute({})
        assert not result.success
        assert "ValidationError" in result.error

    def test_execute_mock_search(self):
        """Execute with mock backend returns results."""
        tool = WebSearchTool(backend="mock")
        result = tool.execute({"query": "aluminum material properties"})
        assert result.success
        assert "results" in result.data
        assert len(result.data["results"]) > 0

    def test_execute_with_num_results(self):
        """Execute respects num_results parameter."""
        tool = WebSearchTool(backend="mock")
        result = tool.execute({"query": "test query", "num_results": 1})
        assert result.success
        assert len(result.data["results"]) <= 1

    def test_get_source_type_authoritative(self):
        """URL containing authoritative domain returns correct type."""
        tool = WebSearchTool()
        assert (
            tool._get_source_type("https://www.iso.org/standard/123")
            == SourceType.AUTHORITATIVE
        )
        assert (
            tool._get_source_type("https://nist.gov/publications")
            == SourceType.AUTHORITATIVE
        )

    def test_get_source_type_vendor(self):
        """URL containing vendor domain returns correct type."""
        tool = WebSearchTool()
        assert (
            tool._get_source_type("https://matweb.com/search/datasheet")
            == SourceType.VENDOR_DATASHEET
        )

    def test_get_source_type_unknown(self):
        """Unknown URL returns UNKNOWN type."""
        tool = WebSearchTool()
        assert (
            tool._get_source_type("https://random-site.com/page") == SourceType.UNKNOWN
        )

    def test_get_source_type_case_insensitive(self):
        """Domain matching is case insensitive."""
        tool = WebSearchTool()
        assert (
            tool._get_source_type("https://ISO.ORG/standard")
            == SourceType.AUTHORITATIVE
        )

    def test_mock_search_aluminum_query(self):
        """Mock search returns aluminum results for material queries."""
        tool = WebSearchTool()
        results = tool._mock_search("aluminum material", 5)
        titles = [r.title.lower() for r in results]
        assert any("aluminum" in t for t in titles)

    def test_mock_search_standard_query(self):
        """Mock search returns standard results for standard queries."""
        tool = WebSearchTool()
        results = tool._mock_search("iso standard tolerances", 5)
        titles = [r.title.lower() for r in results]
        assert any("iso" in t or "tolerance" in t for t in titles)

    def test_mock_search_stress_query(self):
        """Mock search returns stress results for stress queries."""
        tool = WebSearchTool()
        results = tool._mock_search("stress analysis load", 5)
        titles = [r.title.lower() for r in results]
        assert any("stress" in t or "analysis" in t for t in titles)

    def test_mock_search_fallback(self):
        """Mock search returns generic result when nothing matches."""
        tool = WebSearchTool()
        results = tool._mock_search("very specific unique query xyz", 5)
        assert len(results) > 0

    def test_serpapi_fallback_no_key(self):
        """SerpAPI falls back to mock when no API key."""
        tool = WebSearchTool(backend="serpapi", api_key=None)
        results = tool._serpapi_search("test query", 5)
        assert len(results) > 0  # Falls back to mock


class TestWebSearchToolIntegration:
    """Integration tests for WebSearchTool."""

    def test_full_search_workflow(self):
        """Full search workflow returns valid results."""
        tool = WebSearchTool()
        result = tool.execute({"query": "ISO 2768 general tolerances"})

        assert result.success
        assert result.data["results"]

        # Check result structure
        first_result = result.data["results"][0]
        assert "title" in first_result
        assert "url" in first_result
        assert "snippet" in first_result
        assert "source_type" in first_result
        assert "confidence" in first_result

    def test_describe_method(self):
        """Describe method returns readable description."""
        tool = WebSearchTool()
        desc = tool.describe()
        assert "WebSearchTool" in desc
        assert "web_search" in desc
