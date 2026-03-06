from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Protocol

from app.modules.full_stat_adv_updater.types.full_adv_stat import FullAdvStat


class FullstatsProvider(Protocol):
    """Object that provides full campaign stats (e.g. WBDataManager)."""

    async def get_full_adv_stat(
        self, adv_ids: list[int], dates: list[date]
    ) -> list[FullAdvStat]: ...


async def get_full_adv_stat_for_adv_ids(
    fullstats_provider: FullstatsProvider,
    adv_ids: set[int],
    threshold_dates: int,
) -> list[FullAdvStat]:
    """Fetch full adv stats for the last threshold_dates days via provider (e.g. hub.wb_data_manager)."""
    today = datetime.now().date()
    dates = [today - timedelta(days=i) for i in range(threshold_dates)]
    return await fullstats_provider.get_full_adv_stat(list(adv_ids), dates)
