"""Unit tests for the cabinet-401 RUN GO contract collector."""

from __future__ import annotations

import json

import pytest

from scripts import a1_cabinet401_run_go_contract_collect as collector

pytestmark = pytest.mark.unit


def test_contract_identity_and_target_scope() -> None:
    """The collector is pinned to the requested shop, cabinet, and NMIDs."""
    assert collector.SHOP_ID == "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
    assert collector.WB_CABINET_ID == 401
    assert len(collector.TARGET_NMIDS) == 8
    assert collector.PRESERVED_DECISIONS["751657528"] == "KEEP_STOPPED"
    assert collector.PRESERVED_DECISIONS["1256595631"] == "SCALE_FIRST"


def test_scenarios_do_not_promote_promo_to_cash() -> None:
    """Funding scenarios explicitly preserve promo-as-non-cash semantics."""
    rows = collector._scenario_rows()
    assert [row["additional_rub"] for row in rows] == [2000, 4000, 6000]
    assert all(row["promo_is_cash"] is False for row in rows)


def test_write_counts_are_zero_and_payload_is_json_serializable() -> None:
    """The write gate stays closed and the contract envelope is serializable."""
    assert all(value == 0 for value in collector.SAFETY_WRITE_COUNTS.values())
    payload = collector._contract_payload({}, {})
    json.dumps(payload, ensure_ascii=False)
    assert payload["stock"]["missing_is_not_zero"] is True
