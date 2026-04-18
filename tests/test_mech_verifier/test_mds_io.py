"""Tests for MDS I/O utilities."""

import json

import pytest

from mech_verify.mds.io import read_mds, write_mds


class TestWriteMds:
    """Tests for write_mds."""

    def test_write_creates_file(self, tmp_path):
        mds = {"schema_version": "mech.mds.v1", "parts": []}
        out_path = tmp_path / "mds.json"

        write_mds(mds, out_path)

        assert out_path.exists()

    def test_write_content(self, tmp_path):
        mds = {"schema_version": "mech.mds.v1", "domain": "mech", "parts": []}
        out_path = tmp_path / "mds.json"

        write_mds(mds, out_path)

        content = json.loads(out_path.read_text())
        assert content == mds

    def test_write_creates_parent_dirs(self, tmp_path):
        mds = {"schema_version": "mech.mds.v1"}
        out_path = tmp_path / "nested" / "dir" / "mds.json"

        write_mds(mds, out_path)

        assert out_path.exists()

    def test_write_indented(self, tmp_path):
        mds = {"schema_version": "mech.mds.v1", "parts": []}
        out_path = tmp_path / "mds.json"

        write_mds(mds, out_path)

        raw = out_path.read_text()
        assert "\n" in raw
        assert "  " in raw

    def test_write_trailing_newline(self, tmp_path):
        mds = {"schema_version": "mech.mds.v1"}
        out_path = tmp_path / "mds.json"

        write_mds(mds, out_path)

        raw = out_path.read_text()
        assert raw.endswith("\n")


class TestReadMds:
    """Tests for read_mds."""

    def test_read_valid(self, tmp_path):
        mds = {"schema_version": "mech.mds.v1", "domain": "mech"}
        out_path = tmp_path / "mds.json"
        out_path.write_text(json.dumps(mds))

        result = read_mds(out_path)

        assert result == mds

    def test_read_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            read_mds(tmp_path / "nonexistent.json")

    def test_read_invalid_json(self, tmp_path):
        out_path = tmp_path / "invalid.json"
        out_path.write_text("not valid json")

        with pytest.raises(json.JSONDecodeError):
            read_mds(out_path)

    def test_roundtrip(self, tmp_path):
        mds = {
            "schema_version": "mech.mds.v1",
            "domain": "mech",
            "parts": [
                {
                    "part_id": "abc123",
                    "name": "test",
                    "mass_props": {"volume": 100.0},
                }
            ],
        }
        out_path = tmp_path / "mds.json"

        write_mds(mds, out_path)
        result = read_mds(out_path)

        assert result == mds
