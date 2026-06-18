"""Unit-тесты fallback мин. CPM из settings."""

from __future__ import annotations
import logging
from unittest.mock import MagicMock

import pytest

from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.core.mp.wb.min_bid_defaults import (
    apply_min_bid_defaults_for_advs,
    default_min_bid_rub,
    resolve_auto_min_bid_rub,
    resolve_search_min_bid_rub,
)

pytestmark = pytest.mark.unit


def _make_adv(*, nmids: list[int], auto_id: int, search_id: int | None = None) -> MagicMock:
    adv = MagicMock()
    adv.nmids = nmids
    adv.auto_adv_id = auto_id
    adv.search_adv_id = search_id
    return adv


def test_default_min_bid_rub_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIN_BID_AUTO_DEFAULT", "100")
    monkeypatch.setenv("MIN_BID_SEARCH_DEFAULT", "500")
    assert default_min_bid_rub(AdvPlacementType.AUTO_ADV) == 100
    assert default_min_bid_rub(AdvPlacementType.SEARCH_ADV) == 500


def test_resolve_search_min_bid_rub_uses_cache_then_default(
        monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MIN_BID_SEARCH_DEFAULT", "100")
    min_bids = AdvMinNmidsBids(auto={}, search={7: 55})
    assert resolve_search_min_bid_rub(7, min_bids) == 55
    assert resolve_search_min_bid_rub(8, min_bids) == 100


def test_resolve_auto_min_bid_rub_invalid_uses_default() -> None:
    min_bids = AdvMinNmidsBids(auto={7: 0}, search={})
    assert resolve_auto_min_bid_rub(7, min_bids) == 100


def test_apply_min_bid_defaults_for_advs_partial_fill(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MIN_BID_AUTO_DEFAULT", "100")
    monkeypatch.setenv("MIN_BID_SEARCH_DEFAULT", "500")

    advs = [_make_adv(nmids=[7, 8], auto_id=300, search_id=301)]
    raw = AdvMinNmidsBids(auto={}, search={7: 60})

    with caplog.at_level(logging.WARNING):
        out = apply_min_bid_defaults_for_advs(raw, advs, context="unit_test")

    assert out.auto == {7: 100, 8: 100}
    assert out.search == {7: 60, 8: 500}
    default_logs = [r for r in caplog.records if "min_bids using default" in r.getMessage()]
    assert len(default_logs) == 3


def test_apply_min_bid_defaults_replaces_invalid_values() -> None:
    advs = [_make_adv(nmids=[1], auto_id=100)]
    raw = AdvMinNmidsBids(auto={1: -5}, search={})
    out = apply_min_bid_defaults_for_advs(raw, advs)
    assert out.auto[1] == 100
