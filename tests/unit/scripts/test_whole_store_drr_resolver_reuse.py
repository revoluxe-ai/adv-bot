"""Unit: ProKraft whole-store-drr request matches shared Registry row."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tools.scripts import registry, resolver

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]
_REQUEST_PATH = (
    _REPO_ROOT
    / ".tmp"
    / "opsx-scripts"
    / "prokraft-store-drr-573-20260921t1407"
    / "REQUEST.json"
)


def _load_prokraft_request() -> dict[str, object]:
    """Загрузить сохранённый ProKraft REQUEST из ops run folder."""
    payload = json.loads(_REQUEST_PATH.read_text(encoding="utf-8"))
    payload["mode"] = "PLAN_RUN"
    return payload


def test_registry_whole_store_drr_row_validates() -> None:
    """Resolution-enabled whole-store row passes Registry v2 validation."""
    document = yaml.safe_load((_REPO_ROOT / "scripts" / "REGISTRY.yaml").read_text(encoding="utf-8"))
    registry.validate_document(document)
    entry = next(e for e in document["entries"] if e["id"] == "a1-whole-store-daily-drr")
    assert entry["resolution_enabled"] is True
    assert "whole-store-drr" in entry["capabilities"]


def test_prokraft_request_compatible_with_whole_store_row() -> None:
    """ProKraft REQUEST contract matches shared whole-store-drr Registry row."""
    request = _load_prokraft_request()
    document = yaml.safe_load((_REPO_ROOT / "scripts" / "REGISTRY.yaml").read_text(encoding="utf-8"))
    entry = next(e for e in document["entries"] if e["id"] == "a1-whole-store-daily-drr")
    assert resolver._compatible(entry, request) is True
