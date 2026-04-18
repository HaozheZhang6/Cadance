"""Tests for SymbolTable canonical registry and alias resolution."""

from src.verification.semantic.symbol_table import CanonicalEntry, SymbolTable


def test_canonical_entry_creation():
    """CanonicalEntry dataclass stores name, dimensionality, unit, aliases."""
    entry = CanonicalEntry(
        canonical_name="payload_mass",
        expected_dimensionality="[mass]",
        canonical_unit="kg",
        aliases=["mass", "design_payload_mass"],
    )
    assert entry.canonical_name == "payload_mass"
    assert entry.expected_dimensionality == "[mass]"
    assert entry.canonical_unit == "kg"
    assert entry.aliases == ["mass", "design_payload_mass"]


def test_register_canonical_builds_alias_map():
    """register_canonical stores entry and builds alias_map."""
    st = SymbolTable()
    st.register_canonical(
        "payload_mass",
        "[mass]",
        "kg",
        ["mass", "design_payload_mass"],
    )

    # Check registry
    assert "payload_mass" in st._registry
    entry = st._registry["payload_mass"]
    assert entry.canonical_name == "payload_mass"
    assert entry.expected_dimensionality == "[mass]"

    # Check alias_map
    assert st._alias_map["mass"] == "payload_mass"
    assert st._alias_map["design_payload_mass"] == "payload_mass"


def test_resolve_returns_canonical_name():
    """resolve returns canonical_name for exact match."""
    st = SymbolTable()
    st.register_canonical("payload_mass", "[mass]", "kg", [])

    canonical, z3_var, is_mapped = st.resolve("payload_mass", "kg")

    assert canonical == "payload_mass"
    assert z3_var is not None
    assert is_mapped is True


def test_resolve_alias_returns_same_canonical():
    """resolve returns same canonical_name for aliases."""
    st = SymbolTable()
    st.register_canonical(
        "payload_mass", "[mass]", "kg", ["mass", "design_payload_mass"]
    )

    canonical1, z3_var1, is_mapped1 = st.resolve("mass", "kg")
    canonical2, z3_var2, is_mapped2 = st.resolve("design_payload_mass", "kg")

    assert canonical1 == "payload_mass"
    assert canonical2 == "payload_mass"
    assert is_mapped1 is True
    assert is_mapped2 is True
    # Both should return same z3_var (identity check)
    assert z3_var1 is z3_var2


def test_resolve_normalizes_param_name():
    """resolve normalizes param_name: lowercase + spaces to underscore."""
    st = SymbolTable()
    st.register_canonical("payload_mass", "[mass]", "kg", [])

    canonical1, z3_var1, is_mapped1 = st.resolve("Payload Mass", "kg")
    canonical2, z3_var2, is_mapped2 = st.resolve("payload_mass", "kg")

    assert canonical1 == "payload_mass"
    assert canonical2 == "payload_mass"
    assert z3_var1 is z3_var2  # Same z3_var


def test_resolve_unmapped_returns_none_z3_var():
    """resolve returns (normalized_name, None, False) for unmapped params."""
    st = SymbolTable()
    st.register_canonical("payload_mass", "[mass]", "kg", [])

    canonical, z3_var, is_mapped = st.resolve("payload_weight", "kg")

    assert canonical == "payload_weight"
    assert z3_var is None
    assert is_mapped is False


def test_resolve_caches_z3_var_identity():
    """Multiple resolve calls return same z3_var object (identity)."""
    st = SymbolTable()
    st.register_canonical("payload_mass", "[mass]", "kg", [])

    canonical1, z3_var1, is_mapped1 = st.resolve("payload_mass", "kg")
    canonical2, z3_var2, is_mapped2 = st.resolve("payload_mass", "kg")

    assert z3_var1 is z3_var2  # Same object in memory


def test_resolve_validates_dimensionality_warns_on_mismatch(caplog):
    """resolve warns on dimensionality mismatch but still returns z3_var."""
    st = SymbolTable()
    st.register_canonical("payload_mass", "[mass]", "kg", [])

    # Use length unit (m) for mass parameter - should warn
    canonical, z3_var, is_mapped = st.resolve("payload_mass", "m")

    assert canonical == "payload_mass"
    assert z3_var is not None  # Still returns z3_var
    assert is_mapped is True
    assert "dimensionality mismatch" in caplog.text.lower()


def test_fuzzy_match_suggests_close_names():
    """fuzzy_match returns close matches from canonicals + aliases."""
    st = SymbolTable()
    st.register_canonical(
        "payload_mass", "[mass]", "kg", ["mass", "design_payload_mass"]
    )
    st.register_canonical("hole_diameter", "[length]", "m", ["diameter"])

    suggestions = st.fuzzy_match("payload_weight", cutoff=0.6, n=3)

    assert "payload_mass" in suggestions or "mass" in suggestions


def test_predefined_canonicals_loaded():
    """SymbolTable loads predefined engineering parameters by default."""
    st = SymbolTable()

    # Check payload_mass
    assert "payload_mass" in st._registry
    assert st._alias_map["mass"] == "payload_mass"
    assert st._alias_map["design_payload_mass"] == "payload_mass"

    # Check hole_diameter
    assert "hole_diameter" in st._registry
    assert st._alias_map["diameter"] == "hole_diameter"
    assert st._alias_map["bore_diameter"] == "hole_diameter"

    # Check plate_thickness
    assert "plate_thickness" in st._registry
    assert st._alias_map["thickness"] == "plate_thickness"
    assert st._alias_map["wall_thickness"] == "plate_thickness"

    # Check safety_factor
    assert "safety_factor" in st._registry
    assert st._alias_map["factor"] == "safety_factor"
    assert st._alias_map["load_factor"] == "safety_factor"

    # Check installation_torque
    assert "installation_torque" in st._registry
    assert st._alias_map["torque"] == "installation_torque"


def test_predefined_canonicals_resolve():
    """Predefined canonicals can be resolved correctly."""
    st = SymbolTable()

    # Test payload_mass resolution
    canonical, z3_var, is_mapped = st.resolve("payload_mass", "kg")
    assert canonical == "payload_mass"
    assert z3_var is not None
    assert is_mapped is True

    # Test alias resolution
    canonical2, z3_var2, is_mapped2 = st.resolve("design_payload_mass", "kg")
    assert canonical2 == "payload_mass"
    assert z3_var2 is z3_var  # Same variable


def test_register_canonical_duplicate_alias_warning(caplog):
    """register_canonical warns on duplicate alias but registry takes precedence."""
    st = SymbolTable()
    st.register_canonical("payload_mass", "[mass]", "kg", ["mass"])
    st.register_canonical("other_mass", "[mass]", "kg", ["mass"])

    assert "already mapped" in caplog.text.lower() or "duplicate" in caplog.text.lower()


def test_canonical_entry_has_domain_class():
    """CanonicalEntry has domain_class field."""
    entry = CanonicalEntry(
        canonical_name="plate_thickness",
        expected_dimensionality="[length]",
        canonical_unit="m",
        aliases=["thickness"],
        domain_class="LENGTH_POS",
    )
    assert entry.domain_class == "LENGTH_POS"


def test_predefined_canonicals_have_domain_class():
    """Predefined canonicals have domain_class assigned."""
    st = SymbolTable()
    # Resolve to ensure it exists
    canonical, z3_var, is_mapped = st.resolve("plate_thickness", "m")
    assert is_mapped is True

    # Check entry has domain_class
    entry = st._registry["plate_thickness"]
    assert hasattr(entry, "domain_class")
    assert entry.domain_class != ""


def test_get_invariants_empty_returns_empty():
    """get_invariants returns empty list when no variables resolved."""
    from src.verification.semantic.symbol_table import get_invariants

    st = SymbolTable()
    # Don't resolve anything - _z3_vars should be empty

    invariants = get_invariants(st)
    assert invariants == []


def test_get_invariants_length_pos():
    """get_invariants generates > 0 constraint for LENGTH_POS."""
    from z3 import Solver, sat

    from src.verification.semantic.symbol_table import get_invariants

    st = SymbolTable()
    canonical, z3_var, is_mapped = st.resolve("plate_thickness", "m")

    invariants = get_invariants(st)

    # Should have one constraint
    assert len(invariants) == 1
    name, constraint = invariants[0]

    # Check name
    assert name == "INV_POS_plate_thickness"

    # Check constraint is z3_var > 0
    # Test by checking if z3_var=1 satisfies constraint
    solver = Solver()
    solver.add(constraint)
    solver.add(z3_var == 1)
    assert solver.check() == sat

    # Test that z3_var=-1 does not satisfy
    solver2 = Solver()
    solver2.add(constraint)
    solver2.add(z3_var == -1)
    assert solver2.check().r != sat.r


def test_get_invariants_factor_ge1():
    """get_invariants generates >= 1 constraint for FACTOR_GE1."""
    from z3 import Solver, sat

    from src.verification.semantic.symbol_table import get_invariants

    st = SymbolTable()
    canonical, z3_var, is_mapped = st.resolve("safety_factor", "")

    invariants = get_invariants(st)

    # Should have one constraint
    assert len(invariants) == 1
    name, constraint = invariants[0]

    # Check name
    assert name == "INV_GE1_safety_factor"

    # Check constraint is z3_var >= 1
    # Test z3_var=1 satisfies
    solver = Solver()
    solver.add(constraint)
    solver.add(z3_var == 1)
    assert solver.check() == sat

    # Test z3_var=0.5 does not satisfy
    solver2 = Solver()
    solver2.add(constraint)
    solver2.add(z3_var == 0.5)
    assert solver2.check().r != sat.r


def test_get_invariants_multiple_vars():
    """get_invariants returns constraints for multiple resolved variables."""
    from src.verification.semantic.symbol_table import get_invariants

    st = SymbolTable()
    st.resolve("plate_thickness", "m")
    st.resolve("safety_factor", "")

    invariants = get_invariants(st)

    # Should have 2 constraints
    assert len(invariants) == 2

    names = [name for name, _ in invariants]
    assert "INV_POS_plate_thickness" in names
    assert "INV_GE1_safety_factor" in names


def test_get_invariants_nonneg():
    """get_invariants generates >= 0 constraint for LENGTH_NONNEG."""
    from z3 import Solver, sat

    from src.verification.semantic.symbol_table import get_invariants

    st = SymbolTable()
    canonical, z3_var, is_mapped = st.resolve("deflection", "m")

    invariants = get_invariants(st)

    # Should have one constraint
    assert len(invariants) == 1
    name, constraint = invariants[0]

    # Check name
    assert name == "INV_NONNEG_deflection"

    # Check constraint is z3_var >= 0
    # Test z3_var=0 satisfies
    solver = Solver()
    solver.add(constraint)
    solver.add(z3_var == 0)
    assert solver.check() == sat

    # Test z3_var=-1 does not satisfy
    solver2 = Solver()
    solver2.add(constraint)
    solver2.add(z3_var == -1)
    assert solver2.check().r != sat.r
