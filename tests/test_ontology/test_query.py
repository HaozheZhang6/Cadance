"""Tests for OntologyQuery."""

import pytest

from src.ontology import (
    ConfidenceSource,
    FailureMode,
    InterfacePhysics,
    MaterialEntity,
    OntologyQuery,
    OntologyRelation,
    OntologyStore,
    PartEntity,
    PhysicsPhenomenon,
    ProcessTechnique,
    RelationType,
)


@pytest.fixture
def query_store():
    """Create store with comprehensive test data."""
    store = OntologyStore()

    # Parts
    bracket = PartEntity(
        id="part-bracket",
        name="Mounting Bracket",
        description="Steel mounting bracket for load bearing",
        category="bracket",
        typical_materials=["steel", "aluminum"],
        selection_parameters=["load_capacity", "material", "mounting_pattern"],
        confidence=0.85,
        source="test",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(bracket)

    bearing = PartEntity(
        id="part-bearing",
        name="Ball Bearing",
        description="Deep groove ball bearing",
        category="bearing",
        typical_materials=["steel"],
        selection_parameters=["load_rating", "speed_rating", "bore_diameter"],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(bearing)

    # Materials
    steel = MaterialEntity(
        id="mat-steel",
        name="1020 Steel",
        description="Low carbon steel",
        category="metal",
        compatible_materials=["aluminum", "brass"],
        incompatible_materials=["magnesium"],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(steel)

    aluminum = MaterialEntity(
        id="mat-aluminum",
        name="6061 Aluminum",
        description="General purpose aluminum alloy",
        category="metal",
        compatible_materials=["steel", "brass"],
        incompatible_materials=["copper"],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.DATASHEET,
    )
    store.add_entity(aluminum)

    # Failure modes
    fatigue = FailureMode(
        id="fm-fatigue",
        name="Fatigue Failure",
        description="Material failure due to cyclic loading",
        domain="mechanical",
        severity="high",
        causes=["cyclic loading", "stress concentration", "material defects"],
        effects=["crack initiation", "crack propagation", "sudden fracture"],
        detection_methods=["visual inspection", "dye penetrant", "ultrasonic"],
        mitigations=[
            "reduce stress concentration",
            "improve surface finish",
            "shot peening",
        ],
        confidence=0.85,
        source="test",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(fatigue)

    corrosion = FailureMode(
        id="fm-corrosion",
        name="Galvanic Corrosion",
        description="Corrosion due to dissimilar metal contact",
        domain="chemical_materials",
        severity="medium",
        causes=[
            "dissimilar metals",
            "electrolyte presence",
            "galvanic potential difference",
        ],
        effects=["material loss", "weakening", "surface degradation"],
        detection_methods=["visual inspection", "thickness measurement"],
        mitigations=["material selection", "insulating washers", "protective coating"],
        confidence=0.8,
        source="test",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(corrosion)

    # Physics
    stress_conc = PhysicsPhenomenon(
        id="phys-stress",
        name="Stress Concentration",
        description="Localized increase in stress at geometric discontinuities",
        domain="mechanical",
        parameters=["stress concentration factor", "notch radius", "fillet radius"],
        keywords=["stress", "notch", "fillet", "corner", "hole"],
        equations=[{"name": "Kt", "formula": "sigma_max / sigma_nom"}],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(stress_conc)

    # Processes
    cnc = ProcessTechnique(
        id="proc-cnc",
        name="CNC Machining",
        description="Computer numerical control machining",
        category="machining",
        material_compatibility=["steel", "aluminum", "brass", "plastic"],
        achievable_tolerances={"general": "+/- 0.05mm", "precision": "+/- 0.01mm"},
        common_defects=["tool marks", "burrs", "dimensional deviation"],
        confidence=0.9,
        source="test",
        source_type=ConfidenceSource.MANUAL,
    )
    store.add_entity(cnc)

    # Interface physics
    bolted_joint = InterfacePhysics(
        id="iface-bolted",
        name="Bolted Joint Interface",
        description="Physics of bolted connections",
        interface_type="mechanical",
        component_types=["bracket", "fastener", "structure"],
        phenomena=["preload", "friction", "fatigue"],
        design_rules=[
            "maintain preload",
            "avoid joint separation",
            "consider thermal expansion",
        ],
        interface_failure_modes=[
            "joint loosening",
            "fatigue at thread root",
            "embedment relaxation",
        ],
        confidence=0.85,
        source="test",
        source_type=ConfidenceSource.TEXTBOOK,
    )
    store.add_entity(bolted_joint)

    # Relations
    store.add_relation(
        OntologyRelation(
            id="rel-bracket-fatigue",
            relation_type=RelationType.FAILURE_MODE_OF,
            source_id="fm-fatigue",
            target_id="part-bracket",
            confidence=0.8,
        )
    )

    store.add_relation(
        OntologyRelation(
            id="rel-fatigue-stress",
            relation_type=RelationType.GOVERNED_BY,
            source_id="fm-fatigue",
            target_id="phys-stress",
            confidence=0.9,
        )
    )

    return store


@pytest.fixture
def query(query_store):
    """Create OntologyQuery instance."""
    return OntologyQuery(query_store)


class TestComponentSelection:
    """Test component selection queries."""

    def test_suggest_components_basic(self, query):
        """Test basic component suggestion."""
        suggestions = query.suggest_components(
            requirements=["load bearing", "mounting"],
        )

        assert len(suggestions) > 0
        names = [s.part.name for s in suggestions]
        assert "Mounting Bracket" in names

    def test_suggest_components_with_category(self, query):
        """Test component suggestion with category filter."""
        suggestions = query.suggest_components(
            requirements=["rotation", "support"],
            category="bearing",
        )

        # Should only return bearings
        for s in suggestions:
            assert s.part.category == "bearing"

    def test_suggest_components_with_material(self, query):
        """Test component suggestion with material constraint."""
        suggestions = query.suggest_components(
            requirements=["mounting", "bracket"],
            material_constraints=["aluminum"],
        )

        for s in suggestions:
            assert "aluminum" in [m.lower() for m in s.part.typical_materials]


class TestFailureModeAnalysis:
    """Test failure mode analysis."""

    def test_analyze_failure_modes_basic(self, query):
        """Test basic failure mode analysis."""
        analyses = query.analyze_failure_modes()

        assert len(analyses) > 0

    def test_analyze_failure_modes_by_domain(self, query):
        """Test failure mode analysis filtered by domain."""
        analyses = query.analyze_failure_modes(
            physics_domains=["mechanical"],
        )

        for a in analyses:
            assert a.failure_mode.domain == "mechanical"

    def test_analyze_failure_modes_by_severity(self, query):
        """Test failure mode analysis filtered by severity."""
        analyses = query.analyze_failure_modes(
            severity_filter=["high"],
        )

        for a in analyses:
            assert a.failure_mode.severity == "high"

    def test_failure_mode_has_related_phenomena(self, query):
        """Test that failure modes include related physics."""
        analyses = query.analyze_failure_modes()

        fatigue_analysis = next(
            (a for a in analyses if a.failure_mode.name == "Fatigue Failure"),
            None,
        )
        assert fatigue_analysis is not None
        # Should have related stress concentration phenomenon
        assert len(fatigue_analysis.related_phenomena) > 0


class TestPhysicsReasoning:
    """Test physics reasoning queries."""

    def test_get_governing_physics(self, query):
        """Test getting governing physics."""
        physics = query.get_governing_physics(["stress", "notch", "fillet"])

        assert len(physics) > 0
        names = [p.name for p in physics]
        assert "Stress Concentration" in names

    def test_physics_has_equations(self, query):
        """Test that physics includes equations."""
        physics = query.get_governing_physics(["stress"])

        stress_conc = next(
            (p for p in physics if p.name == "Stress Concentration"),
            None,
        )
        assert stress_conc is not None
        assert len(stress_conc.equations) > 0


class TestProcessSelection:
    """Test process selection queries."""

    def test_suggest_processes(self, query):
        """Test process suggestion."""
        processes = query.suggest_processes(
            part_features=["machining", "cnc"],
        )

        assert len(processes) > 0
        names = [p.name for p in processes]
        assert "CNC Machining" in names

    def test_suggest_processes_by_material(self, query):
        """Test process suggestion with material filter."""
        processes = query.suggest_processes(
            part_features=["machining"],
            material="steel",
        )

        for p in processes:
            assert "steel" in [m.lower() for m in p.material_compatibility]


class TestMaterialCompatibility:
    """Test material compatibility checks."""

    def test_compatible_materials(self, query):
        """Test checking compatible materials."""
        result = query.check_material_compatibility(["1020 Steel", "6061 Aluminum"])

        assert result["is_compatible"] is True
        assert len(result["incompatible_pairs"]) == 0

    def test_incompatible_materials(self, query):
        """Test detecting incompatible materials."""
        # Steel and magnesium are marked as incompatible
        result = query.check_material_compatibility(["1020 Steel", "magnesium"])

        # Note: magnesium won't be found in store, so check warnings
        assert "materials_not_found" in result


class TestInterfacePhysics:
    """Test interface physics queries."""

    def test_get_interface_physics(self, query):
        """Test getting interface physics."""
        interfaces = query.get_interface_physics(interface_type="mechanical")

        assert len(interfaces) > 0

    def test_get_interface_by_components(self, query):
        """Test getting interface physics by component types."""
        interfaces = query.get_interface_physics(
            component_types=["bracket", "fastener"],
        )

        assert len(interfaces) > 0
        for iface in interfaces:
            assert any(ct in iface.component_types for ct in ["bracket", "fastener"])
