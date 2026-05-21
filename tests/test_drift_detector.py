"""Tests for DriftDetector and ConfigLoader."""

import json
from unittest.mock import MagicMock

import pytest
import yaml

from driftcheck.config_loader import ConfigLoader, ConfigLoaderError
from driftcheck.drift_detector import DriftDetector, DriftResult
from driftcheck.git_reader import GitReaderError


# ---------------------------------------------------------------------------
# ConfigLoader tests
# ---------------------------------------------------------------------------


def _make_loader(raw: str) -> ConfigLoader:
    reader = MagicMock()
    reader.read_file.return_value = raw
    return ConfigLoader(git_reader=reader)


def test_load_yaml_returns_dict():
    data = {"replicas": 3, "image": "myapp:1.0"}
    loader = _make_loader(yaml.dump(data))
    result = loader.load("deploy.yaml")
    assert result == data


def test_load_json_returns_dict():
    data = {"replicas": 2, "image": "myapp:2.0"}
    loader = _make_loader(json.dumps(data))
    result = loader.load("deploy.json")
    assert result == data


def test_load_unsupported_extension_raises():
    loader = _make_loader("")
    with pytest.raises(ConfigLoaderError, match="Unsupported file extension"):
        loader.load("deploy.toml")


def test_load_git_error_raises_config_loader_error():
    reader = MagicMock()
    reader.read_file.side_effect = GitReaderError("not found")
    loader = ConfigLoader(git_reader=reader)
    with pytest.raises(ConfigLoaderError, match="Failed to read"):
        loader.load("missing.yaml")


def test_load_invalid_yaml_raises():
    loader = _make_loader(": : invalid: yaml: [")
    with pytest.raises(ConfigLoaderError, match="Failed to parse"):
        loader.load("bad.yaml")


def test_load_non_mapping_raises():
    loader = _make_loader(yaml.dump(["a", "b", "c"]))
    with pytest.raises(ConfigLoaderError, match="Expected a mapping"):
        loader.load("list.yaml")


# ---------------------------------------------------------------------------
# DriftDetector tests
# ---------------------------------------------------------------------------


def test_no_drift_when_configs_equal():
    cfg = {"replicas": 3, "image": "app:1"}
    result = DriftDetector().compare(cfg, cfg.copy())
    assert not result.has_drift


def test_detects_added_keys():
    result = DriftDetector().compare({"a": 1}, {"a": 1, "b": 2})
    assert result.added == {"b": 2}
    assert not result.removed
    assert not result.changed


def test_detects_removed_keys():
    result = DriftDetector().compare({"a": 1, "b": 2}, {"a": 1})
    assert result.removed == {"b": 2}
    assert not result.added


def test_detects_changed_values():
    result = DriftDetector().compare({"replicas": 3}, {"replicas": 5})
    assert result.changed == {"replicas": (3, 5)}
    assert result.has_drift


def test_drift_result_path_stored():
    result = DriftDetector().compare({}, {}, path="services/api.yaml")
    assert result.path == "services/api.yaml"
