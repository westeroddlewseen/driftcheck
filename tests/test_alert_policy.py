"""Tests for AlertPolicy and alert_policy_loader."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from driftcheck.alert_policy import AlertPolicy, AlertPolicyError
from driftcheck.alert_policy_loader import load_alert_policy


# ---------------------------------------------------------------------------
# AlertPolicy unit tests
# ---------------------------------------------------------------------------

def test_default_policy_allows_single_drift():
    policy = AlertPolicy()
    assert policy.should_alert(["svc-a"]) is True


def test_below_min_drifted_services_no_alert():
    policy = AlertPolicy(min_drifted_services=3)
    assert policy.should_alert(["svc-a", "svc-b"]) is False


def test_meets_min_drifted_services_alerts():
    policy = AlertPolicy(min_drifted_services=2)
    assert policy.should_alert(["svc-a", "svc-b"]) is True


def test_ignored_services_excluded_from_count():
    policy = AlertPolicy(min_drifted_services=2, ignored_services=["canary"])
    # Only "svc-a" counts; "canary" is ignored → below threshold
    assert policy.should_alert(["svc-a", "canary"]) is False


def test_require_image_drift_blocks_when_false():
    policy = AlertPolicy(require_image_drift=True)
    assert policy.should_alert(["svc-a"], image_drifted=False) is False


def test_require_image_drift_passes_when_true():
    policy = AlertPolicy(require_image_drift=True)
    assert policy.should_alert(["svc-a"], image_drifted=True) is True


def test_invalid_min_raises():
    with pytest.raises(AlertPolicyError, match="min_drifted_services"):
        AlertPolicy(min_drifted_services=0)


def test_from_dict_parses_correctly():
    policy = AlertPolicy.from_dict(
        {"min_drifted_services": 2, "ignored_services": ["x"], "require_image_drift": True}
    )
    assert policy.min_drifted_services == 2
    assert policy.ignored_services == ["x"]
    assert policy.require_image_drift is True


def test_from_dict_bad_value_raises():
    with pytest.raises(AlertPolicyError):
        AlertPolicy.from_dict({"min_drifted_services": "not-a-number"})


# ---------------------------------------------------------------------------
# alert_policy_loader tests
# ---------------------------------------------------------------------------

def test_load_default_policy_succeeds():
    """Bundled YAML should parse without errors."""
    policy = load_alert_policy()
    assert isinstance(policy, AlertPolicy)
    assert policy.min_drifted_services >= 1


def test_load_custom_policy_file(tmp_path: Path):
    cfg = tmp_path / "policy.yaml"
    cfg.write_text(
        textwrap.dedent("""\
            min_drifted_services: 3
            ignored_services:
              - staging
            require_image_drift: true
        """)
    )
    policy = load_alert_policy(str(cfg))
    assert policy.min_drifted_services == 3
    assert "staging" in policy.ignored_services
    assert policy.require_image_drift is True


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(AlertPolicyError, match="Cannot read"):
        load_alert_policy(str(tmp_path / "nonexistent.yaml"))


def test_load_invalid_yaml_raises(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(": : invalid: yaml: [")
    with pytest.raises(AlertPolicyError, match="YAML parse error"):
        load_alert_policy(str(bad))


def test_load_non_mapping_yaml_raises(tmp_path: Path):
    bad = tmp_path / "list.yaml"
    bad.write_text("- item1\n- item2\n")
    with pytest.raises(AlertPolicyError, match="Expected a YAML mapping"):
        load_alert_policy(str(bad))
