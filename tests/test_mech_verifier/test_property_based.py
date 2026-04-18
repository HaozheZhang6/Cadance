"""
Property-based tests for mech_verifier using Hypothesis.

Tests invariants and edge cases through randomized input generation.
"""

from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from verifier_core.models import (
    ArtifactRef,
    Finding,
    Location,
    Severity,
    Unknown,
)

try:
    from mech_verify.tier0_part import (
        Tier0PartResult,
        _generate_finding_id,
        _generate_unknown_id,
        check_degenerate_geometry,
        check_material_present_if_process_given,
        check_units_present,
        normalize_tier0_findings,
        run_tier0_part_checks,
    )
except ImportError:
    from src.mech_verifier.mech_verify.tier0_part import (
        Tier0PartResult,
        _generate_finding_id,
        _generate_unknown_id,
        check_degenerate_geometry,
        check_material_present_if_process_given,
        check_units_present,
        normalize_tier0_findings,
        run_tier0_part_checks,
    )


# =============================================================================
# Hypothesis Strategies
# =============================================================================


# Dimension strategy for realistic CAD values
dimension_strategy = st.floats(
    min_value=0.001, max_value=10000.0, allow_nan=False, allow_infinity=False
)

# Extreme dimension strategy for edge cases
extreme_dimension_strategy = st.floats(
    min_value=1e-12, max_value=1e12, allow_nan=False, allow_infinity=False
)

# Safe text strategy (no null bytes which break things)
safe_text = st.text(
    alphabet=st.characters(
        blacklist_categories=("Cs",),  # No surrogates
        blacklist_characters=("\x00",),  # No null bytes
    ),
    min_size=0,
    max_size=100,
)

# Identifier strategy (alphanumeric + underscore)
identifier_strategy = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-",
    min_size=1,
    max_size=50,
)

# Unicode text for name fields
unicode_text = st.text(min_size=0, max_size=200)


@st.composite
def severity_strategy(draw):
    """Generate a valid Severity enum value."""
    return draw(
        st.sampled_from(
            [
                Severity.BLOCKER,
                Severity.ERROR,
                Severity.WARN,
                Severity.INFO,
                Severity.UNKNOWN,
            ]
        )
    )


@st.composite
def artifact_ref_strategy(draw):
    """Generate valid ArtifactRef objects."""
    kind = draw(st.sampled_from(["step_part", "ops_program", "mds", "output"]))
    # ArtifactRef requires either uri or path
    use_path = draw(st.booleans())
    if use_path:
        path = draw(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./",
                min_size=1,
                max_size=100,
            )
        )
        return ArtifactRef(kind=kind, path=path)
    else:
        uri = "file://" + draw(
            st.text(
                alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-./",
                min_size=1,
                max_size=100,
            )
        )
        return ArtifactRef(kind=kind, uri=uri)


@st.composite
def location_strategy(draw):
    """Generate valid Location objects."""
    has_uri = draw(st.booleans())
    has_region = draw(st.booleans())

    uri = draw(st.text(min_size=1, max_size=100)) if has_uri else None
    region = None
    if has_region:
        start_line = draw(st.integers(min_value=1, max_value=10000))
        start_col = draw(st.integers(min_value=0, max_value=1000))
        region = {
            "startLine": start_line,
            "startColumn": start_col,
            "endLine": draw(
                st.integers(min_value=start_line, max_value=start_line + 100)
            ),
            "endColumn": draw(st.integers(min_value=0, max_value=1000)),
        }

    return Location(uri=uri, region=region)


@st.composite
def finding_strategy(draw):
    """Generate random but valid Finding objects."""
    rule_id = draw(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789._",
            min_size=1,
            max_size=50,
        )
    )
    severity = draw(severity_strategy())
    message = draw(safe_text)
    object_ref = draw(st.one_of(st.none(), safe_text))

    # Optionally add measured value
    measured_value = None
    if draw(st.booleans()):
        measured_value = draw(
            st.one_of(
                st.floats(allow_nan=False, allow_infinity=False),
                st.integers(),
                st.text(max_size=50),
            )
        )

    # Optionally add tags
    tags = []
    if draw(st.booleans()):
        tags = draw(st.lists(identifier_strategy, max_size=5))

    return Finding(
        rule_id=rule_id,
        severity=severity,
        message=message,
        object_ref=object_ref,
        measured_value=measured_value,
        tags=tags,
    )


@st.composite
def unknown_strategy(draw):
    """Generate random but valid Unknown objects."""
    summary = draw(safe_text)
    impact = draw(safe_text)
    resolution_plan = draw(safe_text)
    blocking = draw(st.booleans())
    object_ref = draw(st.one_of(st.none(), safe_text))
    created_by_rule_id = draw(st.one_of(st.none(), identifier_strategy))

    return Unknown(
        summary=summary,
        impact=impact,
        resolution_plan=resolution_plan,
        blocking=blocking,
        object_ref=object_ref,
        created_by_rule_id=created_by_rule_id,
    )


@st.composite
def bbox_strategy(draw):
    """Generate valid bounding box."""
    # Generate min point
    min_x = draw(
        st.floats(
            min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    min_y = draw(
        st.floats(
            min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    min_z = draw(
        st.floats(
            min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )

    # Generate dimensions (positive)
    dim_x = draw(dimension_strategy)
    dim_y = draw(dimension_strategy)
    dim_z = draw(dimension_strategy)

    return {
        "min_point": [min_x, min_y, min_z],
        "max_point": [min_x + dim_x, min_y + dim_y, min_z + dim_z],
        "dimensions": [dim_x, dim_y, dim_z],
    }


@st.composite
def mass_props_strategy(draw):
    """Generate valid mass properties."""
    volume = draw(
        st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False)
    )
    surface_area = draw(
        st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False)
    )

    com_x = draw(
        st.floats(
            min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    com_y = draw(
        st.floats(
            min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )
    com_z = draw(
        st.floats(
            min_value=-10000.0, max_value=10000.0, allow_nan=False, allow_infinity=False
        )
    )

    bbox = draw(bbox_strategy())

    return {
        "volume": volume,
        "surface_area": surface_area,
        "center_of_mass": [com_x, com_y, com_z],
        "bbox": bbox,
    }


@st.composite
def part_strategy(draw):
    """Generate random but valid part dict."""
    part_id = draw(identifier_strategy)
    name = draw(st.one_of(identifier_strategy, unicode_text))

    mass_props = draw(mass_props_strategy())

    # Optionally add material
    material = None
    if draw(st.booleans()):
        material = draw(
            st.sampled_from(
                ["aluminum_6061", "steel_304", "titanium_gr5", "abs_plastic"]
            )
        )

    part = {
        "part_id": part_id,
        "name": name,
        "object_ref": f"mech://part/{part_id}",
        "mass_props": mass_props,
    }

    if material:
        part["material"] = material

    return part


@st.composite
def feature_strategy(draw):
    """Generate random but valid feature dict."""
    feature_type = draw(
        st.sampled_from(["hole", "fillet", "chamfer", "pocket", "boss"])
    )
    feature_id = f"{feature_type}_{draw(st.integers(min_value=0, max_value=999))}"

    parameters = {}
    if feature_type == "hole":
        parameters["diameter"] = draw(dimension_strategy)
        parameters["depth"] = draw(dimension_strategy)
    elif feature_type == "fillet":
        parameters["radius"] = draw(dimension_strategy)
    elif feature_type == "chamfer":
        parameters["distance1"] = draw(dimension_strategy)
        parameters["distance2"] = draw(dimension_strategy)

    return {
        "feature_id": feature_id,
        "feature_type": feature_type,
        "object_ref": f"mech://part/test/feature/{feature_id}",
        "parameters": parameters,
    }


@st.composite
def units_strategy(draw):
    """Generate valid units specification."""
    length_units = ["mm", "cm", "m", "in", "ft"]
    angle_units = ["deg", "rad"]

    has_length = draw(st.booleans())
    has_angle = draw(st.booleans())

    if not has_length and not has_angle:
        has_length = True  # At least one

    units = {}
    if has_length:
        units["length"] = draw(st.sampled_from(length_units))
    if has_angle:
        units["angle"] = draw(st.sampled_from(angle_units))

    return units


@st.composite
def mds_strategy(draw):
    """Generate random but valid MDS (Mechanical Design Snapshot) structures."""
    # Units - can be missing, partial, or complete
    has_units = draw(st.booleans())
    units = draw(units_strategy()) if has_units else None

    # Parts - 0 to 5 parts
    num_parts = draw(st.integers(min_value=0, max_value=5))
    parts = [draw(part_strategy()) for _ in range(num_parts)]

    # Features - 0 to 10 features
    num_features = draw(st.integers(min_value=0, max_value=10))
    features = [draw(feature_strategy()) for _ in range(num_features)]

    mds = {
        "schema_version": "mech.mds.v1",
        "domain": "mech",
        "source_artifacts": [],
        "parts": parts,
        "assemblies": [],
        "features": features,
        "pmi": {
            "has_semantic_pmi": draw(st.booleans()),
            "has_graphical_pmi": draw(st.booleans()),
        },
    }

    if units:
        mds["units"] = units

    return mds


# =============================================================================
# Property Tests - Finding ID Determinism
# =============================================================================


class TestFindingIdDeterminism:
    """Tests for deterministic finding ID generation."""

    @given(st.text(), st.text(), st.text())
    def test_finding_id_helper_is_deterministic(self, rule_id, obj_ref, message):
        """Same inputs always produce same finding ID via helper."""
        id1 = _generate_finding_id(rule_id, obj_ref, message)
        id2 = _generate_finding_id(rule_id, obj_ref, message)
        assert id1 == id2

    @given(st.text(), st.text(), st.text())
    def test_finding_id_helper_is_16_chars(self, rule_id, obj_ref, message):
        """Finding ID helper always produces 16-char hex string."""
        fid = _generate_finding_id(rule_id, obj_ref, message)
        assert len(fid) == 16
        assert all(c in "0123456789abcdef" for c in fid)

    @given(identifier_strategy, st.one_of(st.none(), safe_text), safe_text)
    def test_unknown_id_helper_is_deterministic(self, summary, rule_id, obj_ref):
        """Same inputs always produce same unknown ID via helper."""
        id1 = _generate_unknown_id(summary, rule_id, obj_ref)
        id2 = _generate_unknown_id(summary, rule_id, obj_ref)
        assert id1 == id2


# =============================================================================
# Property Tests - Tier0 Checks
# =============================================================================


class TestTier0CheckInvariants:
    """Tests for Tier-0 check invariants."""

    @given(mds_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_tier0_checks_never_crash(self, mds):
        """Tier0 checks should handle any valid MDS without crashing."""
        result = run_tier0_part_checks(mds)

        assert isinstance(result, Tier0PartResult)
        assert isinstance(result.findings, list)
        assert isinstance(result.unknowns, list)
        assert all(isinstance(f, Finding) for f in result.findings)
        assert all(isinstance(u, Unknown) for u in result.unknowns)

    @given(mds_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_tier0_findings_have_required_fields(self, mds):
        """All tier0 findings have required fields."""
        result = run_tier0_part_checks(mds)

        for finding in result.findings:
            assert finding.rule_id is not None
            assert finding.severity is not None
            assert finding.message is not None
            assert isinstance(finding.severity, Severity)

    @given(mds_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_tier0_unknowns_have_required_fields(self, mds):
        """All tier0 unknowns have required fields."""
        result = run_tier0_part_checks(mds)

        for unknown in result.unknowns:
            assert unknown.summary is not None
            assert unknown.impact is not None
            assert unknown.resolution_plan is not None

    @given(mds_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_missing_units_creates_unknown(self, mds):
        """MDS without units should always produce Unknown."""
        if "units" not in mds or mds.get("units") is None:
            results = check_units_present(mds)
            assert len(results) >= 1
            assert any(isinstance(r, Unknown) for r in results)

    @given(mds_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_units_with_length_no_unknown(self, mds):
        """MDS with length unit should not produce blocking unknown for units."""
        if mds.get("units") and "length" in mds["units"]:
            results = check_units_present(mds)
            # Should have no unknowns about missing units
            unit_unknowns = [
                r
                for r in results
                if isinstance(r, Unknown) and "unit" in r.summary.lower()
            ]
            assert len(unit_unknowns) == 0


# =============================================================================
# Property Tests - Severity Ordering
# =============================================================================


class TestSeverityOrdering:
    """Tests for Severity enum properties."""

    @given(severity_strategy())
    def test_severity_has_value(self, sev):
        """All severities have a string value."""
        assert sev.value is not None
        assert isinstance(sev.value, str)

    @given(severity_strategy(), severity_strategy())
    def test_severity_equality_reflexive(self, sev1, sev2):
        """Severity equality is consistent."""
        if sev1 == sev2:
            assert sev1.value == sev2.value
        else:
            assert sev1.value != sev2.value

    @given(st.sampled_from(list(Severity)))
    def test_severity_roundtrip_via_value(self, sev):
        """Severity can roundtrip through value."""
        value = sev.value
        restored = Severity(value)
        assert restored == sev


# =============================================================================
# Property Tests - Finding Serialization
# =============================================================================


class TestFindingRoundtrip:
    """Tests for Finding serialization roundtrip."""

    @given(finding_strategy())
    @settings(max_examples=100)
    def test_finding_to_dict_keys(self, finding):
        """Finding.to_dict() always includes required keys."""
        d = finding.to_dict()

        assert "rule_id" in d
        assert "severity" in d
        assert "message" in d
        assert d["rule_id"] == finding.rule_id
        assert d["message"] == finding.message

    @given(finding_strategy())
    @settings(max_examples=100)
    def test_finding_severity_serializes_to_string(self, finding):
        """Finding severity serializes to string value."""
        d = finding.to_dict()

        assert isinstance(d["severity"], str)
        # Should be a valid Severity value
        assert d["severity"] in [s.value for s in Severity]

    @given(unknown_strategy())
    @settings(max_examples=100)
    def test_unknown_to_dict_keys(self, unknown):
        """Unknown.to_dict() always includes required keys."""
        d = unknown.to_dict()

        assert "summary" in d
        assert "impact" in d
        assert "resolution_plan" in d


# =============================================================================
# Property Tests - Degenerate Geometry Detection
# =============================================================================


class TestDegenerateGeometryDetection:
    """Tests for degenerate geometry detection."""

    @given(
        st.floats(min_value=-1e12, max_value=0.0, allow_nan=False, allow_infinity=False)
    )
    def test_zero_or_negative_volume_detected(self, bad_volume):
        """Zero or negative volume always produces BLOCKER."""
        mds = {
            "parts": [
                {
                    "part_id": "test_part",
                    "object_ref": "mech://part/test_part",
                    "mass_props": {
                        "volume": bad_volume,
                        "bbox": {"dimensions": [1.0, 1.0, 1.0]},
                    },
                }
            ],
        }

        findings = check_degenerate_geometry(mds)

        volume_findings = [f for f in findings if "volume" in f.message.lower()]
        assert len(volume_findings) >= 1
        assert all(f.severity == Severity.BLOCKER for f in volume_findings)

    @given(
        st.floats(
            min_value=1e-10, max_value=1e10, allow_nan=False, allow_infinity=False
        )
    )
    def test_positive_volume_no_volume_finding(self, good_volume):
        """Positive volume should not produce volume-related BLOCKER."""
        mds = {
            "parts": [
                {
                    "part_id": "test_part",
                    "object_ref": "mech://part/test_part",
                    "mass_props": {
                        "volume": good_volume,
                        "bbox": {"dimensions": [1.0, 1.0, 1.0]},
                    },
                }
            ],
        }

        findings = check_degenerate_geometry(mds)

        volume_findings = [f for f in findings if "volume" in f.message.lower()]
        assert len(volume_findings) == 0

    @given(
        st.lists(
            st.floats(
                min_value=-100.0, max_value=0.0, allow_nan=False, allow_infinity=False
            ),
            min_size=3,
            max_size=3,
        )
    )
    def test_degenerate_bbox_detected(self, bad_dims):
        """Degenerate bbox (any dim <= 0) produces BLOCKER."""
        assume(any(d <= 0 for d in bad_dims))

        mds = {
            "parts": [
                {
                    "part_id": "test_part",
                    "object_ref": "mech://part/test_part",
                    "mass_props": {
                        "volume": 100.0,
                        "bbox": {"dimensions": bad_dims},
                    },
                }
            ],
        }

        findings = check_degenerate_geometry(mds)

        bbox_findings = [f for f in findings if "bounding box" in f.message.lower()]
        assert len(bbox_findings) >= 1


# =============================================================================
# Property Tests - Edge Cases (Fuzz Testing)
# =============================================================================


class TestEdgeCases:
    """Fuzz testing for edge cases."""

    @given(
        st.floats(
            min_value=1e-15, max_value=1e-10, allow_nan=False, allow_infinity=False
        )
    )
    @settings(max_examples=50)
    def test_very_small_dimensions_handled(self, tiny_dim):
        """Very small dimensions don't crash checks."""
        mds = {
            "units": {"length": "mm"},
            "parts": [
                {
                    "part_id": "tiny_part",
                    "object_ref": "mech://part/tiny_part",
                    "mass_props": {
                        "volume": tiny_dim**3,
                        "bbox": {"dimensions": [tiny_dim, tiny_dim, tiny_dim]},
                    },
                }
            ],
        }

        # Should not crash
        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)

    @given(
        st.floats(min_value=1e6, max_value=1e12, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=50)
    def test_very_large_dimensions_handled(self, huge_dim):
        """Very large dimensions don't crash checks."""
        mds = {
            "units": {"length": "mm"},
            "parts": [
                {
                    "part_id": "huge_part",
                    "object_ref": "mech://part/huge_part",
                    "mass_props": {
                        "volume": huge_dim**3 if huge_dim < 1e4 else 1e12,
                        "bbox": {"dimensions": [huge_dim, huge_dim, huge_dim]},
                    },
                }
            ],
        }

        # Should not crash
        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)

    @given(st.text(min_size=1, max_size=500))
    @settings(max_examples=50)
    def test_unicode_names_handled(self, unicode_name):
        """Unicode characters in names don't crash checks."""
        mds = {
            "units": {"length": "mm"},
            "parts": [
                {
                    "part_id": "unicode_part",
                    "name": unicode_name,
                    "object_ref": "mech://part/unicode_part",
                    "mass_props": {
                        "volume": 100.0,
                        "bbox": {"dimensions": [10.0, 10.0, 10.0]},
                    },
                }
            ],
        }

        # Should not crash
        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)

    def test_empty_parts_list_handled(self):
        """Empty parts list doesn't crash."""
        mds = {
            "units": {"length": "mm"},
            "parts": [],
            "features": [],
        }

        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)
        assert len(result.findings) == 0

    def test_empty_mds_handled(self):
        """Minimal/empty MDS doesn't crash."""
        mds = {}

        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)

    @given(st.integers(min_value=0, max_value=50))
    @settings(max_examples=30)
    def test_many_parts_handled(self, num_parts):
        """Many parts don't cause issues."""
        parts = []
        for i in range(num_parts):
            parts.append(
                {
                    "part_id": f"part_{i}",
                    "object_ref": f"mech://part/part_{i}",
                    "mass_props": {
                        "volume": 100.0,
                        "bbox": {"dimensions": [10.0, 10.0, 10.0]},
                    },
                }
            )

        mds = {
            "units": {"length": "mm"},
            "parts": parts,
        }

        result = run_tier0_part_checks(mds)
        assert isinstance(result, Tier0PartResult)


# =============================================================================
# Property Tests - Normalize Findings
# =============================================================================


class TestNormalizeFindings:
    """Tests for findings normalization."""

    @given(st.lists(finding_strategy(), max_size=20))
    @settings(max_examples=50)
    def test_normalize_removes_finding_id(self, findings):
        """Normalization removes finding_id for determinism."""
        normalized = normalize_tier0_findings(findings)

        assert isinstance(normalized, list)
        assert len(normalized) == len(findings)
        for d in normalized:
            assert "finding_id" not in d

    @given(st.lists(finding_strategy(), max_size=20))
    @settings(max_examples=50)
    def test_normalize_is_deterministic(self, findings):
        """Normalizing the same findings twice gives same result."""
        norm1 = normalize_tier0_findings(findings)
        norm2 = normalize_tier0_findings(findings)

        assert norm1 == norm2

    @given(st.lists(finding_strategy(), max_size=20))
    @settings(max_examples=50)
    def test_normalize_preserves_content(self, findings):
        """Normalization preserves finding content (except id)."""
        normalized = normalize_tier0_findings(findings)

        for d in normalized:
            assert "rule_id" in d
            assert "severity" in d
            assert "message" in d


# =============================================================================
# Property Tests - Material/Process Checks
# =============================================================================


class TestMaterialProcessChecks:
    """Tests for material/process validation."""

    @given(identifier_strategy)
    @settings(max_examples=50)
    def test_process_without_material_creates_unknown(self, process_name):
        """Process specified without material creates Unknown."""
        mds = {
            "parts": [
                {
                    "part_id": "test_part",
                    "object_ref": "mech://part/test_part",
                    # No material specified
                }
            ],
        }
        process_info = {"name": process_name}

        unknowns = check_material_present_if_process_given(mds, process_info)

        assert len(unknowns) >= 1
        assert all(isinstance(u, Unknown) for u in unknowns)
        assert all(u.blocking for u in unknowns)

    @given(identifier_strategy, identifier_strategy)
    @settings(max_examples=50)
    def test_process_with_material_no_unknown(self, process_name, material):
        """Process specified with material creates no Unknown."""
        mds = {
            "parts": [
                {
                    "part_id": "test_part",
                    "object_ref": "mech://part/test_part",
                    "material": material,
                }
            ],
        }
        process_info = {"name": process_name}

        unknowns = check_material_present_if_process_given(mds, process_info)

        assert len(unknowns) == 0

    def test_no_process_no_material_check(self):
        """No process means no material check."""
        mds = {
            "parts": [
                {
                    "part_id": "test_part",
                    "object_ref": "mech://part/test_part",
                    # No material
                }
            ],
        }

        # No process info
        unknowns = check_material_present_if_process_given(mds, None)
        assert len(unknowns) == 0

        # Empty process info
        unknowns = check_material_present_if_process_given(mds, {})
        assert len(unknowns) == 0


# =============================================================================
# Property Tests - Tier0PartResult
# =============================================================================


class TestTier0PartResult:
    """Tests for Tier0PartResult properties."""

    @given(st.lists(finding_strategy(), max_size=10))
    @settings(max_examples=50)
    def test_passed_with_no_blockers_or_errors(self, findings):
        """passed is True when no BLOCKER or ERROR findings."""
        result = Tier0PartResult(findings=findings)

        has_blocker_or_error = any(
            f.severity in (Severity.BLOCKER, Severity.ERROR) for f in findings
        )

        assert result.passed == (not has_blocker_or_error)

    @given(st.lists(finding_strategy(), max_size=10))
    @settings(max_examples=50)
    def test_has_blockers_property(self, findings):
        """has_blockers correctly identifies BLOCKER severity."""
        result = Tier0PartResult(findings=findings)

        has_blocker = any(f.severity == Severity.BLOCKER for f in findings)

        assert result.has_blockers == has_blocker
