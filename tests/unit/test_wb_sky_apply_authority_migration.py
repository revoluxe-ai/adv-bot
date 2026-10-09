"""Alembic revision chain for Apply Authority ledger."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_apply_ledger_migration_revision_chain() -> None:
    path = (
        Path(__file__).resolve().parents[2]
        / "alembic_/versions/f9c0a1b2d3e4_add_wb_sky_apply_authority_ledger.py"
    )
    spec = importlib.util.spec_from_file_location("apply_ledger_migration", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.revision == "f9c0a1b2d3e4"
    assert module.down_revision == "e8a1b2c3d4e5"
