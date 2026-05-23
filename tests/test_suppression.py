"""Tests for driftcheck.suppression and driftcheck.suppression_loader."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from driftcheck.suppression import (
    SuppressionManager,
    SuppressionReport,
    SuppressionRule,
)
from driftcheck.suppression_loader import _parse_rules, load_suppression_manager


# ---------------------------------------------------------------------------
# SuppressionRule.matches
# ---------------------------------------------------------------------------

def test_rule_matches_exact_service_and_field():
    rule = SuppressionRule(service="payments", fields=["image"])
    assert rule.matches("payments", "image") is True


def test_rule_does_not_match_wrong_service():
    rule = SuppressionRule(service="payments", fields=["image"])
    assert rule.matches("orders", "image") is False


def test_rule_glob_matches_wildcard():
    rule = SuppressionRule(service="payments-*", fields=["image"])
    assert rule.matches("payments-canary", "image") is True
    assert rule.matches("payments-stable", "image") is True
    assert rule.matches("orders", "image") is False


def test_rule_empty_fields_suppresses_all():
    rule = SuppressionRule(service="sandbox-*", fields=[])
    assert rule.matches("sandbox-demo", "image") is True
    assert rule.matches("sandbox-demo", "replicas") is True


def test_rule_field_not_in_list_not_suppressed():
    rule = SuppressionRule(service="payments", fields=["image"])
    assert rule.matches("payments", "replicas") is False


# ---------------------------------------------------------------------------
# SuppressionManager
# ---------------------------------------------------------------------------

def test_is_suppressed_returns_true_when_rule_matches():
    mgr = SuppressionManager(rules=[SuppressionRule(service="svc", fields=["image"])])
    assert mgr.is_suppressed("svc", "image") is True


def test_is_suppressed_returns_false_when_no_rules():
    mgr = SuppressionManager()
    assert mgr.is_suppressed("svc", "image") is False


def test_filter_drift_fields_splits_correctly():
    mgr = SuppressionManager(
        rules=[SuppressionRule(service="payments", fields=["image"])]
    )
    report: SuppressionReport = mgr.filter_drift_fields(
        "payments", ["image", "replicas"]
    )
    assert "payments:image" in report.suppressed
    assert "payments:replicas" in report.active
    assert report.any_suppressed is True


def test_filter_drift_fields_all_active_when_no_rules():
    mgr = SuppressionManager()
    report = mgr.filter_drift_fields("svc", ["image", "replicas"])
    assert report.suppressed == []
    assert len(report.active) == 2
    assert report.any_suppressed is False


# ---------------------------------------------------------------------------
# suppression_loader
# ---------------------------------------------------------------------------

def test_parse_rules_missing_service_raises():
    from driftcheck.suppression import SuppressionError
    with pytest.raises(SuppressionError, match="service"):
        _parse_rules([{"fields": ["image"]}])


def test_load_suppression_manager_missing_file_returns_empty(tmp_path):
    mgr = load_suppression_manager(config_path=tmp_path / "nope.yaml")
    assert isinstance(mgr, SuppressionManager)
    assert mgr.rules == []


def test_load_suppression_manager_parses_rules(tmp_path):
    cfg = tmp_path / "suppression.yaml"
    cfg.write_text(
        "suppression:\n"
        "  rules:\n"
        "    - service: \"canary-*\"\n"
        "      fields:\n"
        "        - image\n"
        "      reason: canary\n"
    )
    mgr = load_suppression_manager(config_path=cfg)
    assert len(mgr.rules) == 1
    assert mgr.rules[0].service == "canary-*"
    assert mgr.rules[0].fields == ["image"]
    assert mgr.rules[0].reason == "canary"


def test_load_suppression_manager_empty_yaml_returns_empty(tmp_path):
    cfg = tmp_path / "suppression.yaml"
    cfg.write_text("{}")
    mgr = load_suppression_manager(config_path=cfg)
    assert mgr.rules == []
