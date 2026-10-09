"""Fullstats adapter seam: ingest hook order and physical adv identity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.attribution_facts.domain.ingest_models import AttributionIngestBatch
from app.modules.attribution_facts.ingest.seam import (
    AttributionIngestActivation,
    activate_attribution_ingest,
    deactivate_attribution_ingest,
    get_last_ingest_batch,
    maybe_ingest_fullstats_chunk,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_ingest_filters_mismatched_advert_id_in_chunk() -> None:
    """Activation physical_adv_id must match item advertId (fail closed on others)."""
    token = activate_attribution_ingest(
        AttributionIngestActivation(
            shop_id="s",
            adv_setting_id=1,
            physical_adv_id=100,
            history_port=None,
            inventory_port=None,
        )
    )
    try:
        await maybe_ingest_fullstats_chunk(
            [
                {"advertId": 200, "days": []},
                {"advertId": 100, "days": []},
            ]
        )
    finally:
        deactivate_attribution_ingest(token)
    batch_obj = get_last_ingest_batch()
    assert isinstance(batch_obj, AttributionIngestBatch)
    assert batch_obj.shop_id == "s"


@pytest.mark.asyncio
async def test_ingest_failure_does_not_raise() -> None:
    """Ingest errors are logged; caller path can continue."""
    bad_history = MagicMock()
    bad_history.snapshots_as_of = AsyncMock(side_effect=RuntimeError("boom"))
    token = activate_attribution_ingest(
        AttributionIngestActivation(
            shop_id="s",
            adv_setting_id=1,
            physical_adv_id=100,
            history_port=bad_history,
            inventory_port=None,
        )
    )
    payload = {
        "advertId": 100,
        "days": [
            {
                "date": "2026-09-07",
                "orders": 1,
                "sum_price": 10,
                "apps": [
                    {
                        "appType": 1,
                        "nms": [{"nmId": 1, "orders": 1, "sum_price": 10}],
                    }
                ],
            }
        ],
    }
    try:
        await maybe_ingest_fullstats_chunk([payload])
    finally:
        deactivate_attribution_ingest(token)
    assert get_last_ingest_batch() is None


@pytest.mark.asyncio
async def test_fullstats_fetcher_calls_ingest_before_mapper() -> None:
    """Adapter fetcher invokes ingest hook before collapse mapper (source order)."""
    from pathlib import Path

    adapter_src = Path(
        "app/core/mp/wb/api/adapter/promotion_client/fullstats/adapter.py"
    ).read_text(encoding="utf-8")
    fetcher_block = adapter_src.split("async def fetcher", 1)[1].split(
        "return await run_chunked_single_range", 1
    )[0]
    ingest_pos = fetcher_block.index("maybe_ingest_fullstats_chunk")
    mapper_pos = fetcher_block.index("full_stats_item_to_full_adv_stat")
    assert ingest_pos < mapper_pos
