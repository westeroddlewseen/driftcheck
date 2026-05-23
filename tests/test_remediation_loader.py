"""Tests for driftcheck.remediation_loader."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from driftcheck.remediation import RemediationAdvisor
from driftcheck.remediation_loader import load_remediation_advisor


def test_load_returns_advisor_instance():
    advisor = load_remediation_advisor()
    assert isinstance(advisor, RemediationAdvisor)


def test_load_default_tracked_fields_include_image():
    advisor = load_remediation_advisor()
    assert "image" in advisor.TRACKED_FIELDS


def test_load_custom_config_overrides_tracked_fields(tmp_path: Path):
    cfg = tmp_path / "rem.yaml"
    cfg.write_text(yaml.dump({"remediation": {"tracked_fields": ["image"]}}))
    advisor = load_remediation_advisor(cfg)
    assert advisor.TRACKED_FIELDS == ("image",)


def test_load_empty_config_uses_defaults(tmp_path: Path):
    cfg = tmp_path / "empty.yaml"
    cfg.write_text("")
    advisor = load_remediation_advisor(cfg)
    assert "image" in advisor.TRACKED_FIELDS


def test_load_missing_remediation_section_uses_defaults(tmp_path: Path):
    cfg = tmp_path / "other.yaml"
    cfg.write_text(yaml.dump({"other": {}}))
    advisor = load_remediation_advisor(cfg)
    assert "replicas" in advisor.TRACKED_FIELDS
