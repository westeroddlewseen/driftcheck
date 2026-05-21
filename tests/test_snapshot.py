"""Tests for snapshot conversion helpers."""

from __future__ import annotations

import pytest

from driftcheck.service_scanner import ServiceConfig
from driftcheck.snapshot import Snapshot, snapshot_from_expected, snapshot_from_live


def test_snapshot_from_live_maps_all_fields() -> None:
    cfg = ServiceConfig(
        name="api",
        image="myrepo/api:v3",
        replicas=2,
        env_vars={"LOG_LEVEL": "info"},
    )
    snap = snapshot_from_live(cfg)
    assert snap.image == "myrepo/api:v3"
    assert snap.replicas == 2
    assert snap.env_vars == {"LOG_LEVEL": "info"}


def test_snapshot_from_live_defaults() -> None:
    cfg = ServiceConfig(name="worker")
    snap = snapshot_from_live(cfg)
    assert snap.image is None
    assert snap.replicas == 1
    assert snap.env_vars == {}


def test_snapshot_from_expected_dict_env() -> None:
    config = {"image": "nginx:1.25", "replicas": 3, "env": {"PORT": "80"}}
    snap = snapshot_from_expected(config)
    assert snap.image == "nginx:1.25"
    assert snap.replicas == 3
    assert snap.env_vars == {"PORT": "80"}


def test_snapshot_from_expected_list_env() -> None:
    config = {
        "image": "app:latest",
        "env": [{"name": "DEBUG", "value": "true"}, {"name": "PORT", "value": "8080"}],
    }
    snap = snapshot_from_expected(config)
    assert snap.env_vars == {"DEBUG": "true", "PORT": "8080"}


def test_snapshot_from_expected_missing_keys_use_defaults() -> None:
    snap = snapshot_from_expected({})
    assert snap.image is None
    assert snap.replicas == 1
    assert snap.env_vars == {}


def test_snapshot_from_expected_invalid_env_type() -> None:
    snap = snapshot_from_expected({"env": "bad-value"})
    assert snap.env_vars == {}


def test_snapshot_as_dict_round_trip() -> None:
    snap = Snapshot(image="img:1", replicas=2, env_vars={"K": "V"})
    d = snap.as_dict()
    assert d == {"image": "img:1", "replicas": 2, "env_vars": {"K": "V"}}
