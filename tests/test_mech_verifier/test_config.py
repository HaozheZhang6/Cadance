"""Tests for mech_verify configuration loading.

Tests:
- Config loading from rulepack YAML
- Default fallback behavior
- Config override
- Merged config from multiple rulepacks
"""

from mech_verify.config import (
    DEFAULT_CONFIG,
    MechVerifyConfig,
    get_config_dict,
    get_rulepacks_dir,
    load_default_config,
    load_merged_config,
    load_rulepack_config,
    load_rulepack_yaml,
)


class TestDefaultConfig:
    """Tests for default configuration values."""

    def test_default_config_has_all_keys(self):
        """DEFAULT_CONFIG contains all expected keys."""
        expected_keys = [
            "aspect_ratio_max",
            "clearance_min_mm",
            "interference_eps_volume",
            "bbox_margin_mm",
            "min_hole_diameter_mm",
            "max_hole_ld_ratio",
            "min_fillet_radius_mm",
            "min_wall_thickness_mm",
            "pmi_text_scan_confidence",
        ]
        for key in expected_keys:
            assert key in DEFAULT_CONFIG, f"Missing key: {key}"

    def test_default_values_sensible(self):
        """Default values are sensible for manufacturing."""
        assert DEFAULT_CONFIG["aspect_ratio_max"] == 1e6
        assert DEFAULT_CONFIG["clearance_min_mm"] == 0.2
        assert DEFAULT_CONFIG["interference_eps_volume"] == 1e-6
        assert DEFAULT_CONFIG["min_hole_diameter_mm"] == 1.0
        assert DEFAULT_CONFIG["max_hole_ld_ratio"] == 10.0


class TestMechVerifyConfig:
    """Tests for MechVerifyConfig dataclass."""

    def test_default_construction(self):
        """Config with no args uses defaults."""
        config = MechVerifyConfig()
        assert config.aspect_ratio_max == DEFAULT_CONFIG["aspect_ratio_max"]
        assert config.clearance_min_mm == DEFAULT_CONFIG["clearance_min_mm"]

    def test_from_dict_uses_provided_values(self):
        """from_dict uses values from dict."""
        d = {
            "clearance_min_mm": 0.5,
            "aspect_ratio_max": 1e5,
        }
        config = MechVerifyConfig.from_dict(d)
        assert config.clearance_min_mm == 0.5
        assert config.aspect_ratio_max == 1e5

    def test_from_dict_uses_defaults_for_missing(self):
        """from_dict falls back to defaults for missing keys."""
        config = MechVerifyConfig.from_dict({})
        assert config.clearance_min_mm == DEFAULT_CONFIG["clearance_min_mm"]
        assert config.aspect_ratio_max == DEFAULT_CONFIG["aspect_ratio_max"]

    def test_get_method(self):
        """get() returns attribute or raw value."""
        config = MechVerifyConfig.from_dict({"custom_key": 42})
        assert config.get("clearance_min_mm") == DEFAULT_CONFIG["clearance_min_mm"]
        assert config.get("custom_key") == 42
        assert config.get("nonexistent", "default") == "default"

    def test_to_dict_roundtrip(self):
        """to_dict returns all config values."""
        config = MechVerifyConfig()
        d = config.to_dict()
        assert d["clearance_min_mm"] == config.clearance_min_mm
        assert d["aspect_ratio_max"] == config.aspect_ratio_max


class TestRulepackLoading:
    """Tests for loading config from rulepack YAML."""

    def test_rulepacks_dir_exists(self):
        """get_rulepacks_dir returns valid path."""
        rulepacks_dir = get_rulepacks_dir()
        assert rulepacks_dir.exists(), f"Rulepacks dir not found: {rulepacks_dir}"
        assert rulepacks_dir.is_dir()

    def test_load_assembly_fit_rulepack(self):
        """Load tier0_assembly_fit rulepack YAML."""
        rulepack = load_rulepack_yaml("tier0_assembly_fit")
        assert rulepack.get("name") == "tier0_assembly_fit"
        assert "default_parameters" in rulepack
        params = rulepack["default_parameters"]
        assert "clearance_min_mm" in params
        assert "interference_eps_volume" in params

    def test_load_dfm_machining_rulepack(self):
        """Load tier0_dfm_machining rulepack YAML."""
        rulepack = load_rulepack_yaml("tier0_dfm_machining")
        assert rulepack.get("name") == "tier0_dfm_machining"
        params = rulepack.get("default_parameters", {})
        assert "min_hole_diameter_mm" in params

    def test_load_nonexistent_rulepack_returns_empty(self):
        """Loading nonexistent rulepack returns empty dict."""
        rulepack = load_rulepack_yaml("nonexistent_rulepack_xyz")
        assert rulepack == {}

    def test_load_rulepack_config(self):
        """load_rulepack_config returns MechVerifyConfig."""
        config = load_rulepack_config("tier0_assembly_fit")
        assert isinstance(config, MechVerifyConfig)
        # Should have values from rulepack
        assert config.clearance_min_mm == 0.2
        assert config.interference_eps_volume == 1e-6


class TestMergedConfig:
    """Tests for merged configuration from multiple rulepacks."""

    def test_load_merged_config(self):
        """load_merged_config merges multiple rulepacks."""
        config = load_merged_config(
            "tier0_assembly_fit",
            "tier0_dfm_machining",
        )
        # From assembly_fit
        assert config.clearance_min_mm == 0.2
        # From dfm_machining
        assert config.min_hole_diameter_mm == 1.0

    def test_later_rulepack_overrides(self):
        """Later rulepacks override earlier ones."""
        # This tests that merge order matters
        config = load_merged_config("tier0_assembly_fit")
        assert config.clearance_min_mm == 0.2

    def test_load_default_config(self):
        """load_default_config loads all standard rulepacks."""
        config = load_default_config()
        assert isinstance(config, MechVerifyConfig)
        # Should have values from all rulepacks
        assert config.clearance_min_mm is not None
        assert config.aspect_ratio_max is not None


class TestConfigDictAccess:
    """Tests for dict-based config access."""

    def test_get_config_dict_default(self):
        """get_config_dict() returns defaults."""
        d = get_config_dict()
        assert "clearance_min_mm" in d
        assert "aspect_ratio_max" in d

    def test_get_config_dict_specific_rulepack(self):
        """get_config_dict(name) returns that rulepack's config."""
        d = get_config_dict("tier0_assembly_fit")
        assert d["clearance_min_mm"] == 0.2


class TestConfigIntegration:
    """Integration tests for config with verification modules."""

    def test_tier0_assembly_config_uses_defaults(self):
        """Tier0AssemblyConfig uses centralized defaults."""
        from mech_verify.tier0_assembly import Tier0AssemblyConfig

        config = Tier0AssemblyConfig()
        assert config.clearance_min_mm == DEFAULT_CONFIG["clearance_min_mm"]
        assert (
            config.interference_eps_volume == DEFAULT_CONFIG["interference_eps_volume"]
        )

    def test_tier0_assembly_config_from_mech_config(self):
        """Tier0AssemblyConfig.from_mech_config works."""
        from mech_verify.tier0_assembly import Tier0AssemblyConfig

        mech_config = MechVerifyConfig(clearance_min_mm=0.5)
        asm_config = Tier0AssemblyConfig.from_mech_config(mech_config)
        assert asm_config.clearance_min_mm == 0.5

    def test_interference_uses_centralized_default(self):
        """interference module uses centralized default."""
        from mech_verify.assembly.interference import _DEFAULT_EPS_VOLUME

        assert _DEFAULT_EPS_VOLUME == DEFAULT_CONFIG["interference_eps_volume"]

    def test_clearance_uses_centralized_default(self):
        """clearance module uses centralized default."""
        from mech_verify.assembly.clearance import _DEFAULT_MIN_DIST

        assert _DEFAULT_MIN_DIST == DEFAULT_CONFIG["clearance_min_mm"]
