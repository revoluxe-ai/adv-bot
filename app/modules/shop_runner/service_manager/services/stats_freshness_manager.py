"""Single entry point for stats freshness check (CH). Used by AdvSettingMenu and CoroutinesManager."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.clickhouse_freshness_reader import (
    ClickHouseStatsFreshnessReader,
)
from app.modules.shop_runner.service_manager.services.stats_freshness_guard import (
    StatsFreshnessGuard,
    StatsFreshnessState,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)


class StatsFreshnessManager:
    """Single entry point for stats freshness evaluation from ClickHouse.
    Used by UI (AdvSettingMenu) and CoroutinesManager. Builds reader + guard and calls evaluate_batch."""

    async def evaluate(self, complex_adv: ComplexAdv) -> StatsFreshnessState:
        reader = ClickHouseStatsFreshnessReader()
        guard = StatsFreshnessGuard(reader)
        return await guard.evaluate_batch(complex_adv)
