"""Tests for verifier_core.rulepack module."""

import json

import pytest

from verifier_core.rulepack.manifest import (
    ManifestLoadError,
    RuleDefinition,
    RulePackManifest,
    load_manifest,
    load_manifest_from_dir,
    validate_manifest,
)
from verifier_core.rulepack.registry import (
    RulePackRegistry,
    discover_rulepacks,
)


class TestRulePackManifest:
    """Tests for RulePackManifest dataclass."""

    def test_basic_manifest(self):
        """Create basic manifest."""
        manifest = RulePackManifest(
            name="test_pack",
            version="1.0.0",
            description="Test rulepack",
        )
        assert manifest.name == "test_pack"
        assert manifest.version == "1.0.0"
        assert manifest.domain is None
        assert manifest.tier is None

    def test_manifest_with_domain_and_tier(self):
        """Create manifest with domain and tier (new-style)."""
        manifest = RulePackManifest(
            name="mech_basic",
            version="1.0.0",
            description="Mechanical basic checks",
            domain="mech",
            tier=0,
            shacl_shapes=["shapes/basic.ttl"],
        )
        assert manifest.domain == "mech"
        assert manifest.tier == 0
        assert manifest.shacl_shapes == ["shapes/basic.ttl"]

    def test_manifest_to_dict(self):
        """Manifest should serialize to dict."""
        manifest = RulePackManifest(
            name="test",
            version="1.0.0",
            description="Test",
            domain="eda",
            tier=0,
        )
        d = manifest.to_dict()
        assert d["name"] == "test"
        assert d["domain"] == "eda"
        assert d["tier"] == 0


class TestRuleDefinition:
    """Tests for RuleDefinition dataclass."""

    def test_basic_rule(self):
        """Create basic rule."""
        rule = RuleDefinition(
            id="test_rule",
            title="Test Rule",
            description="A test rule",
            severity="warning",
        )
        assert rule.id == "test_rule"
        assert rule.enabled is True
        assert rule.waivable is True

    def test_rule_to_dict(self):
        """Rule should serialize to dict."""
        rule = RuleDefinition(
            id="test",
            title="Test",
            description="Desc",
            severity="error",
            tags=["safety"],
        )
        d = rule.to_dict()
        assert d["id"] == "test"
        assert d["tags"] == ["safety"]


class TestLoadManifest:
    """Tests for manifest loading functions."""

    def test_load_json_manifest(self, tmp_path):
        """Load manifest from JSON file."""
        manifest_data = {
            "name": "test_pack",
            "version": "1.0.0",
            "description": "Test rulepack",
            "rules": [
                {
                    "id": "rule1",
                    "title": "Rule 1",
                    "description": "First rule",
                    "severity": "warning",
                    "scope": "board",
                    "predicate": "x > 0",
                }
            ],
        }
        manifest_path = tmp_path / "rulepack.json"
        manifest_path.write_text(json.dumps(manifest_data))

        manifest = load_manifest(manifest_path)
        assert manifest.name == "test_pack"
        assert len(manifest.rules) == 1
        assert manifest.rules[0].id == "rule1"

    def test_load_manifest_missing_required_field(self, tmp_path):
        """Loading manifest without required fields should raise."""
        manifest_data = {
            "name": "test",
            # missing version and description
        }
        manifest_path = tmp_path / "bad.json"
        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestLoadError, match="Missing required"):
            load_manifest(manifest_path)

    def test_load_manifest_nonexistent_file(self, tmp_path):
        """Loading nonexistent file should raise."""
        with pytest.raises(ManifestLoadError, match="not found"):
            load_manifest(tmp_path / "nonexistent.json")

    def test_load_manifest_with_new_style_fields(self, tmp_path):
        """Load manifest with domain/tier/shacl_shapes (new-style)."""
        manifest_data = {
            "name": "mech_tier0",
            "version": "1.0.0",
            "description": "Mechanical tier 0 checks",
            "domain": "mech",
            "tier": 0,
            "shacl_shapes": ["shapes/constraints.ttl"],
        }
        manifest_path = tmp_path / "rulepack.json"
        manifest_path.write_text(json.dumps(manifest_data))

        manifest = load_manifest(manifest_path)
        assert manifest.domain == "mech"
        assert manifest.tier == 0
        assert "shapes/constraints.ttl" in manifest.shacl_shapes


class TestLoadManifestFromDir:
    """Tests for directory-based manifest loading."""

    def test_load_from_directory(self, tmp_path):
        """Load manifest from directory structure."""
        # Create directory structure
        pack_dir = tmp_path / "my_pack"
        pack_dir.mkdir()
        rules_dir = pack_dir / "rules"
        rules_dir.mkdir()

        # Create manifest
        manifest_data = {
            "name": "my_pack",
            "version": "1.0.0",
            "description": "My rulepack",
            "pack_tags": ["manufacturing"],
        }
        (pack_dir / "rulepack.json").write_text(json.dumps(manifest_data))

        # Create a rule file
        rule_data = {
            "id": "dir_rule",
            "title": "Dir Rule",
            "description": "Rule from directory",
            "severity": "error",
            "scope": "component",
            "predicate": "len(parts) > 0",
        }
        (rules_dir / "rule1.json").write_text(json.dumps(rule_data))

        manifest = load_manifest_from_dir(pack_dir)
        assert manifest.name == "my_pack"
        assert len(manifest.rules) == 1
        assert manifest.rules[0].id == "dir_rule"
        # Pack tags should be applied to rules
        assert "manufacturing" in manifest.rules[0].tags

    def test_load_from_dir_auto_discover_shapes(self, tmp_path):
        """SHACL shapes in shapes/ dir should be auto-discovered."""
        pack_dir = tmp_path / "shacl_pack"
        pack_dir.mkdir()
        shapes_dir = pack_dir / "shapes"
        shapes_dir.mkdir()

        # Create manifest
        manifest_data = {
            "name": "shacl_pack",
            "version": "1.0.0",
            "description": "Pack with SHACL shapes",
            "domain": "eda",
            "tier": 0,
        }
        (pack_dir / "rulepack.json").write_text(json.dumps(manifest_data))

        # Create a shape file
        (shapes_dir / "constraints.ttl").write_text("# SHACL shapes")

        manifest = load_manifest_from_dir(pack_dir)
        assert "shapes/constraints.ttl" in manifest.shacl_shapes


class TestValidateManifest:
    """Tests for manifest validation."""

    def test_valid_manifest(self):
        """Valid manifest should have no errors."""
        manifest = RulePackManifest(
            name="test",
            version="1.0.0",
            description="Test",
            rules=[
                RuleDefinition(
                    id="r1",
                    title="R1",
                    description="Rule 1",
                    severity="warning",
                    predicate="x > 0",
                )
            ],
        )
        errors = validate_manifest(manifest)
        assert len(errors) == 0

    def test_duplicate_rule_ids(self):
        """Duplicate rule IDs should be flagged."""
        manifest = RulePackManifest(
            name="test",
            version="1.0.0",
            description="Test",
            rules=[
                RuleDefinition(
                    id="r1",
                    title="R1",
                    description="D1",
                    severity="warn",
                    predicate="x",
                ),
                RuleDefinition(
                    id="r1",
                    title="R2",
                    description="D2",
                    severity="warn",
                    predicate="y",
                ),
            ],
        )
        errors = validate_manifest(manifest)
        assert any("Duplicate" in e for e in errors)

    def test_invalid_tier(self):
        """Invalid tier should be flagged."""
        manifest = RulePackManifest(
            name="test",
            version="1.0.0",
            description="Test",
            tier=99,
        )
        errors = validate_manifest(manifest)
        assert any("Tier" in e for e in errors)

    def test_invalid_domain(self):
        """Invalid domain should be flagged."""
        manifest = RulePackManifest(
            name="test",
            version="1.0.0",
            description="Test",
            domain="invalid",
        )
        errors = validate_manifest(manifest)
        assert any("domain" in e for e in errors)


class TestRulePackRegistry:
    """Tests for RulePackRegistry."""

    def test_register_and_get(self):
        """Register and retrieve a manifest."""
        registry = RulePackRegistry()
        manifest = RulePackManifest(
            name="test_pack",
            version="1.0.0",
            description="Test",
        )
        registry.register(manifest)

        retrieved = registry.get("test_pack")
        assert retrieved is not None
        assert retrieved.name == "test_pack"

    def test_filter_by_domain(self):
        """Filter rulepacks by domain."""
        registry = RulePackRegistry()
        registry.register(
            RulePackManifest(
                name="eda1", version="1.0.0", description="D", domain="eda"
            )
        )
        registry.register(
            RulePackManifest(
                name="mech1", version="1.0.0", description="D", domain="mech"
            )
        )
        registry.register(
            RulePackManifest(
                name="eda2", version="1.0.0", description="D", domain="eda"
            )
        )

        eda_packs = registry.filter_by_domain("eda")
        assert len(eda_packs) == 2
        assert all(p.domain == "eda" for p in eda_packs)

    def test_filter_by_tier(self):
        """Filter rulepacks by tier."""
        registry = RulePackRegistry()
        registry.register(
            RulePackManifest(name="t0", version="1.0.0", description="D", tier=0)
        )
        registry.register(
            RulePackManifest(name="t1", version="1.0.0", description="D", tier=1)
        )
        registry.register(
            RulePackManifest(name="t0b", version="1.0.0", description="D", tier=0)
        )

        tier0_packs = registry.filter_by_tier(0)
        assert len(tier0_packs) == 2

    def test_list_all(self):
        """List all registered packs."""
        registry = RulePackRegistry()
        registry.register(RulePackManifest(name="a", version="1.0.0", description="D"))
        registry.register(RulePackManifest(name="b", version="1.0.0", description="D"))

        all_packs = registry.list_all()
        assert len(all_packs) == 2


class TestDiscoverRulepacks:
    """Tests for discover_rulepacks function."""

    def test_discover_from_paths(self, tmp_path):
        """Discover rulepacks from path list."""
        # Create two rulepack directories
        pack1 = tmp_path / "pack1"
        pack1.mkdir()
        (pack1 / "rulepack.json").write_text(
            json.dumps({"name": "pack1", "version": "1.0.0", "description": "P1"})
        )

        pack2 = tmp_path / "pack2"
        pack2.mkdir()
        (pack2 / "rulepack.json").write_text(
            json.dumps(
                {
                    "name": "pack2",
                    "version": "1.0.0",
                    "description": "P2",
                    "domain": "mech",
                }
            )
        )

        discovered = discover_rulepacks([tmp_path])
        assert len(discovered) == 2

    def test_discover_with_domain_filter(self, tmp_path):
        """Discover with domain filter."""
        pack1 = tmp_path / "eda_pack"
        pack1.mkdir()
        (pack1 / "rulepack.json").write_text(
            json.dumps(
                {"name": "eda", "version": "1.0.0", "description": "D", "domain": "eda"}
            )
        )

        pack2 = tmp_path / "mech_pack"
        pack2.mkdir()
        (pack2 / "rulepack.json").write_text(
            json.dumps(
                {
                    "name": "mech",
                    "version": "1.0.0",
                    "description": "D",
                    "domain": "mech",
                }
            )
        )

        discovered = discover_rulepacks([tmp_path], domain="mech")
        assert len(discovered) == 1
        assert discovered[0].domain == "mech"
