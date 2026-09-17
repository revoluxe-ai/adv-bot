"""Unit tests for the generic multi-client read-only preflight collector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import multi_client_ad_preflight_collect as collector

pytestmark = pytest.mark.unit


def _identity(cabinet: int = 573, nmid: int = 1285392243) -> collector.RunIdentity:
    """Create the authoritative test identity."""
    return collector.RunIdentity(
        shop_id="5586b2ff-449c-4151-9518-60f46d32b7d9",
        wb_cabinet_id=cabinet,
        target_nmid=nmid,
        client_size_id=1895360146,
    )


def test_cabinet_573_cannot_emit_401(tmp_path: Path) -> None:
    """A foreign cabinet in any payload is rejected before packaging."""
    (tmp_path / "payload.json").write_text(
        json.dumps({"wb_cabinet_id": 401}), encoding="utf-8"
    )
    assert collector.reconcile_identity(tmp_path, _identity()) == [
        "wb_cabinet_id: expected=573, got=401"
    ]


def test_ownership_mismatch_fails(tmp_path: Path) -> None:
    """A foreign shop identity fails closed."""
    (tmp_path / "payload.json").write_text(
        json.dumps({"shop_id": "foreign-shop"}), encoding="utf-8"
    )
    assert collector.reconcile_identity(tmp_path, _identity())


def test_target_ownership_mismatch_fails(tmp_path: Path) -> None:
    """A row for a different target NMID cannot enter the envelope."""
    (tmp_path / "payload.json").write_text(
        json.dumps({"target_nmid": 4010000000}), encoding="utf-8"
    )
    assert collector.reconcile_identity(tmp_path, _identity())


def test_semantic_guards_preserve_required_distinctions() -> None:
    """CPC/Search, stock, period, and attribution semantics stay explicit."""
    payload = {
        "stock": {"missing_is_not_zero": True},
        "campaigns": {"cpc_is_not_bot_search": True},
        "economics": {
            "factual_is_not_attributed": True,
        },
        "periods": {"open_closed_distinct": True},
    }
    assert collector.validate_semantics(payload) == []


def test_missing_stock_stays_missing_and_cpc_is_not_search() -> None:
    """The semantic gate rejects accidental zeroing or campaign relabeling."""
    payload = {
        "stock": {"missing_is_not_zero": False},
        "campaigns": {"cpc_is_not_bot_search": False},
        "economics": {"factual_is_not_attributed": True},
        "periods": {"open_closed_distinct": True},
    }
    errors = collector.validate_semantics(payload)
    assert "missing stock was not preserved as missing" in errors
    assert "CPC was not separated from bot Search" in errors


def test_open_closed_and_factual_attributed_are_distinct() -> None:
    """The payload contract requires both temporal and economic distinctions."""
    payload = {
        "stock": {"missing_is_not_zero": True},
        "campaigns": {"cpc_is_not_bot_search": True},
        "economics": {"factual_is_not_attributed": False},
        "periods": {"open_closed_distinct": False},
    }
    errors = collector.validate_semantics(payload)
    assert "factual and attributed economics were conflated" in errors
    assert "open and closed periods were conflated" in errors


def test_no_production_mutation_path() -> None:
    """The collector's declared write counters are all zero."""
    assert collector.WRITE_COUNTS == {
        "ALL_PRODUCTION_WRITES": 0,
        "WB_API_WRITES": 0,
        "POSTGRES_WRITES": 0,
        "CLICKHOUSE_WRITES": 0,
        "REDIS_WRITES": 0,
    }
