"""Нормализация WB normquery bids к search_adv_id."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.modules.cluster_bids_redis import ClusterBidKey
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.update_cluster_bids_manager import (
    _normalize_cluster_bids_to_search_adv_id,
)


@pytest.mark.unit
def test_normalize_maps_auto_advert_id_to_search_adv_id() -> None:
    """Legacy WB ответ с auto advert_id попадает в индекс по search_adv_id."""
    sub_adv = MagicMock()
    sub_adv.auto_adv_id = 32824944
    sub_adv.auction_adv_id = 29734515

    fresh = [
        NormqueryBidDTO(
            advert_id=32824944,
            nm_id=10749810,
            norm_query="крем",
            bid=510,
        )
    ]
    needed = {29734515}

    by_key = _normalize_cluster_bids_to_search_adv_id(fresh, [sub_adv], needed)

    key = ClusterBidKey(search_adv_id=29734515, nmid=10749810, cluster="крем")
    assert key in by_key
    assert by_key[key].advert_id == 29734515
    assert by_key[key].bid == 510
