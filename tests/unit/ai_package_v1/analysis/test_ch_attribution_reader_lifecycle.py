"""CH attribution collection uses one client per export batch."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.ai_package_v1.analysis.attribution_reader import (
    ChAnalysisAttributionReader,
    collect_attribution_evidence,
)
from app.modules.ai_package_v1.keyword_performance.windows.engine import WindowSpec

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_ch_reader_single_client_for_all_cells() -> None:
    reader = ChAnalysisAttributionReader()
    windows = [
        WindowSpec("w1", date(2026, 10, 1), date(2026, 10, 1)),
        WindowSpec("w2", date(2026, 10, 2), date(2026, 10, 2)),
    ]
    legs = [(111, "AUTO"), (222, "SEARCH")]

    client = MagicMock()
    client_cm = AsyncMock()
    client_cm.__aenter__.return_value = client
    client_cm.__aexit__.return_value = None

    acquire_count = 0

    def fake_get_client() -> object:
        nonlocal acquire_count
        acquire_count += 1
        return client_cm

    with (
        patch(
            "app.utils.click_house.client.get_clickhouse_client",
            side_effect=fake_get_client,
        ),
        patch(
            "app.modules.attribution_facts.readers.ch_attribution_facts_reader.ChAttributionFactsReader",
        ) as ch_reader_cls,
        patch(
            "app.modules.ai_package_v1.analysis.attribution_reader.PortAnalysisAttributionReader"
        ) as port_cls,
    ):
        port = port_cls.return_value
        port.query_leg_window = AsyncMock(
            return_value=MagicMock(facts=(), coverage=MagicMock())
        )
        ch_reader_cls.return_value = MagicMock()

        await collect_attribution_evidence(
            reader,
            shop_id="shop",
            windows=windows,
            legs=legs,
        )

    assert acquire_count == 1
    assert port.query_leg_window.await_count == 4
