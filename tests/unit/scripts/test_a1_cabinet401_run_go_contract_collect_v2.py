"""Unit tests for the isolated cabinet-401 RUN GO collector."""

from __future__ import annotations

import json

import pytest

from scripts import a1_cabinet401_run_go_contract_collect_v2 as collector

pytestmark = pytest.mark.unit


def test_contract_identity_and_preserved_decisions() -> None:
    """The corrected collector keeps the exact requested identity and decisions."""
    assert collector.SHOP_ID == "5339e9ad-cbfe-50fc-8d77-b9f337a80417"
    assert collector.WB_CABINET_ID == 401
    assert collector.TARGET_NMIDS == (
        1256595631,
        451263613,
        645328132,
        525419807,
        217149845,
        255636259,
        751657528,
        214754056,
    )
    assert collector.PRESERVED_DECISIONS == {
        "751657528": "KEEP_STOPPED",
        "1256595631": "SCALE_FIRST",
    }


def test_contract_payload_preserves_zero_write_and_gap_semantics() -> None:
    """Payload remains serializable and never turns missing stock into zero."""
    payload = collector._contract_payload({}, {})
    json.dumps(payload, ensure_ascii=False)
    assert payload["stock"]["missing_is_not_zero"] is True
    assert payload["funding"]["promo_is_cash"] is False
    assert all(value == 0 for value in collector.SAFETY_WRITE_COUNTS.values())

