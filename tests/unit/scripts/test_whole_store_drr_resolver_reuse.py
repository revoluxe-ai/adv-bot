"""Unit: whole-store-drr Registry row validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tools.scripts import registry

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_registry_whole_store_drr_row_validates() -> None:
    """Resolution-enabled whole-store row passes Registry v2 validation."""
    document = yaml.safe_load((_REPO_ROOT / "scripts" / "REGISTRY.yaml").read_text(encoding="utf-8"))
    registry.validate_document(document)
    entry = next(e for e in document["entries"] if e["id"] == "a1-whole-store-daily-drr")
    assert entry["resolution_enabled"] is True
    assert "whole-store-drr" in entry["capabilities"]
