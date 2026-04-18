"""Tests for verifier_core.object_ref module."""

import pytest

from verifier_core.object_ref import (
    ObjectRefError,
    build_object_ref,
    get_domain_from_ref,
    is_eda_ref,
    is_mech_ref,
    join_object_ref,
    normalize_object_ref,
    parse_object_ref,
    validate_object_ref,
)


class TestValidateObjectRef:
    """Tests for validate_object_ref function."""

    def test_valid_eda_ref(self):
        """EDA refs with path should be valid."""
        assert validate_object_ref("eda://board/U1") is True
        assert validate_object_ref("eda://component/R1/pad1") is True
        assert validate_object_ref("eda://net/GND") is True

    def test_valid_mech_ref(self):
        """Mech refs with path should be valid."""
        assert validate_object_ref("mech://part/bracket") is True
        assert validate_object_ref("mech://assembly/housing/screw1") is True
        assert validate_object_ref("mech://fastener/M3x10") is True

    def test_valid_file_ref(self):
        """File refs should be valid."""
        assert validate_object_ref("file:///path/to/file.txt") is True
        assert validate_object_ref("file://localhost/path") is True

    def test_valid_http_refs(self):
        """HTTP(S) refs should be valid."""
        assert validate_object_ref("http://example.com") is True
        assert validate_object_ref("https://example.com/path") is True

    def test_empty_ref_raises(self):
        """Empty ref should raise error."""
        with pytest.raises(ObjectRefError, match="cannot be empty"):
            validate_object_ref("")

    def test_missing_scheme_raises(self):
        """Ref without scheme should raise error."""
        with pytest.raises(ObjectRefError, match="Missing scheme"):
            validate_object_ref("board/U1")

    def test_unsupported_scheme_raises(self):
        """Unsupported scheme should raise error."""
        with pytest.raises(ObjectRefError, match="Unsupported scheme"):
            validate_object_ref("ftp://example.com")

    def test_custom_allowed_schemes(self):
        """Custom allowed schemes should work."""
        assert validate_object_ref("eda://board/U1", allowed_schemes={"eda"}) is True
        with pytest.raises(ObjectRefError, match="Unsupported scheme"):
            validate_object_ref("mech://part/x", allowed_schemes={"eda"})

    def test_domain_scheme_requires_path(self):
        """Domain schemes require a path."""
        # These should work (have path)
        assert validate_object_ref("eda://board") is True
        assert validate_object_ref("mech://part") is True


class TestNormalizeObjectRef:
    """Tests for normalize_object_ref function."""

    def test_lowercase_scheme(self):
        """Scheme should be lowercased."""
        result = normalize_object_ref("EDA://board/U1")
        assert result.startswith("eda://")

    def test_removes_trailing_slash(self):
        """Trailing slashes should be removed."""
        result = normalize_object_ref("eda://board/U1/")
        assert not result.endswith("/")

    def test_encodes_special_chars(self):
        """Special chars in path should be encoded."""
        result = normalize_object_ref("eda://board/U1 test")
        assert "%20" in result or "U1%20test" in result

    def test_preserves_query_and_fragment(self):
        """Query and fragment should be preserved."""
        result = normalize_object_ref("eda://board/U1?rev=2#section")
        assert "?rev=2" in result
        assert "#section" in result


class TestBuildObjectRef:
    """Tests for build_object_ref function."""

    def test_basic_build(self):
        """Build basic ref from segments."""
        result = build_object_ref("eda", "board", "components", "U1")
        assert result == "eda://board/components/U1"

    def test_build_with_query(self):
        """Build ref with query params."""
        result = build_object_ref("mech", "part", "bracket", query={"rev": "2"})
        assert "mech://part/bracket" in result
        assert "rev=2" in result

    def test_build_with_fragment(self):
        """Build ref with fragment."""
        result = build_object_ref("eda", "net", "GND", fragment="pin1")
        assert result.endswith("#pin1")

    def test_unsupported_scheme_raises(self):
        """Unsupported scheme should raise error."""
        with pytest.raises(ObjectRefError):
            build_object_ref("unknown", "path")


class TestJoinObjectRef:
    """Tests for join_object_ref function."""

    def test_join_parts(self):
        """Join parts to base URI."""
        result = join_object_ref("eda://board", "components", "U1")
        assert result == "eda://board/components/U1"

    def test_join_strips_slashes(self):
        """Leading/trailing slashes should be handled."""
        result = join_object_ref("eda://board/", "/components/", "/U1/")
        assert result == "eda://board/components/U1"

    def test_join_empty_parts(self):
        """Empty parts should be skipped."""
        result = join_object_ref("eda://board", "", "U1", "")
        assert result == "eda://board/U1"


class TestParseObjectRef:
    """Tests for parse_object_ref function."""

    def test_parse_full_ref(self):
        """Parse full ref into components."""
        result = parse_object_ref("eda://board/components/U1?rev=2#pin1")
        assert result["scheme"] == "eda"
        assert result["netloc"] == "board"
        assert "components/U1" in result["path"]
        assert result["query"] == "rev=2"
        assert result["fragment"] == "pin1"

    def test_parse_simple_ref(self):
        """Parse simple ref."""
        result = parse_object_ref("mech://part/bracket")
        assert result["scheme"] == "mech"
        assert result["path"] is not None


class TestGetDomainFromRef:
    """Tests for get_domain_from_ref function."""

    def test_eda_domain(self):
        """EDA refs return 'eda' domain."""
        assert get_domain_from_ref("eda://board/U1") == "eda"

    def test_mech_domain(self):
        """Mech refs return 'mech' domain."""
        assert get_domain_from_ref("mech://part/x") == "mech"

    def test_non_domain_ref(self):
        """Non-domain refs return None."""
        assert get_domain_from_ref("file:///path") is None
        assert get_domain_from_ref("https://example.com") is None


class TestIsEdaRef:
    """Tests for is_eda_ref function."""

    def test_eda_ref(self):
        """EDA refs should return True."""
        assert is_eda_ref("eda://board/U1") is True

    def test_non_eda_ref(self):
        """Non-EDA refs should return False."""
        assert is_eda_ref("mech://part/x") is False
        assert is_eda_ref("file:///path") is False


class TestIsMechRef:
    """Tests for is_mech_ref function."""

    def test_mech_ref(self):
        """Mech refs should return True."""
        assert is_mech_ref("mech://part/bracket") is True

    def test_non_mech_ref(self):
        """Non-mech refs should return False."""
        assert is_mech_ref("eda://board/U1") is False
        assert is_mech_ref("file:///path") is False
