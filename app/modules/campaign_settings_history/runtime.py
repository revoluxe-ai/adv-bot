"""Runtime composition for campaign settings history.

Spec: campaign-settings-history.
No DDL, no WB writes, no current-settings writes.
"""

from __future__ import annotations

from app.utils.click_house.clickhouse_protocol import ClickHouseClientProtocol
from app.utils.db.session_maker import get_async_session_maker

from .clickhouse_repository import ClickHouseCampaignSettingsHistoryRepository
from .collector import collect_cabinet
from .coordinator import (
    PostgresTransactionCoordinator,
    locked_cabinet_transaction,
)
from .domain import CabinetCollectResult
from .pg_reader import PostgresCampaignSettingsReader


async def discover_history_cabinet_ids() -> tuple[int, ...]:
    """Read PG settings ownership without Redis/active-campaign filters."""
    async with get_async_session_maker(read_only=True) as session:
        return await PostgresCampaignSettingsReader(session).discover_cabinet_ids()


async def collect_one_locked_cabinet(
    *,
    wb_cabinet_id: int,
    clickhouse_client: ClickHouseClientProtocol,
) -> CabinetCollectResult:
    """Own one PG xact lock, then read PG and append changed CH snapshots."""
    async with locked_cabinet_transaction(wb_cabinet_id) as locked:
        if not locked.acquired:
            return CabinetCollectResult(
                wb_cabinet_id=wb_cabinet_id,
                code="lock_contended",
            )
        reader = PostgresCampaignSettingsReader(locked.session)
        coordinator = PostgresTransactionCoordinator(locked.session)
        history = ClickHouseCampaignSettingsHistoryRepository(clickhouse_client)
        return await collect_cabinet(
            wb_cabinet_id=wb_cabinet_id,
            reader=reader,
            history=history,
            coordinator=coordinator,
        )
