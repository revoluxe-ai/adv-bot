from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.shop_runner.service_manager.services.clickhouse_freshness_reader import (
    ClickHouseStatsFreshnessReader,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.settings import settings


@dataclass(frozen=True)
class StatsFreshnessState:
    is_fresh: bool
    is_stale_over_6h: bool
    reason: str | None = None


class StatsFreshnessGuard:
    """Centralized guard for campaign automation based on stats freshness."""

    _EMERGENCY_STALE_PERIOD = timedelta(hours=6)

    def __init__(
        self,
        ch_freshness_reader: ClickHouseStatsFreshnessReader,
    ) -> None:
        self._ch_reader = ch_freshness_reader

    async def evaluate_batch(self, complex_adv: ComplexAdv) -> StatsFreshnessState:
        """Like evaluate() but fetches all three timestamps in one semaphore+session.
        Use from UI (e.g. AdvSettingMenu) to reduce CH contention."""
        common_updated_at, full_adv_updated_at, cluster_updated_at = (
            await self._ch_reader.get_all_updated_ats(complex_adv)
        )
        return self._state_from_timestamps(
            complex_adv, common_updated_at, full_adv_updated_at, cluster_updated_at
        )

    async def evaluate(self, complex_adv: ComplexAdv) -> StatsFreshnessState:
        common_updated_at = await self._ch_reader.get_common_updated_at(complex_adv)
        full_adv_updated_at = await self._ch_reader.get_full_adv_updated_at(complex_adv)
        cluster_updated_at = await self._ch_reader.get_cluster_updated_at(complex_adv)
        return self._state_from_timestamps(
            complex_adv, common_updated_at, full_adv_updated_at, cluster_updated_at
        )

    def _state_from_timestamps(
        self,
        complex_adv: ComplexAdv,
        common_updated_at: datetime | None,
        full_adv_updated_at: datetime | None,
        cluster_updated_at: datetime | None,
    ) -> StatsFreshnessState:
        now = datetime.now(timezone.utc)
        fresh_period = timedelta(seconds=settings.UPDATE_FULL_ADV_STAT_PERIOD)
        adv_id_repr = complex_adv.original_adv_setting_id

        common_age = self._calc_age(now, common_updated_at)
        full_adv_age = self._calc_age(now, full_adv_updated_at)
        cluster_age = self._calc_age(now, cluster_updated_at)

        source_ages: dict[str, timedelta | None] = {
            "common_stat_update": common_age,
            "full_adv_stat_update": full_adv_age,
            "cluster_stat_update": cluster_age,
        }
        for source, age in source_ages.items():
            if age is None:
                return StatsFreshnessState(
                    is_fresh=False,
                    is_stale_over_6h=False,
                    reason=f"{source} not yet collected for adv_id={adv_id_repr}",
                )
            if age > self._EMERGENCY_STALE_PERIOD:
                return StatsFreshnessState(
                    is_fresh=False,
                    is_stale_over_6h=True,
                    reason=f"{source} stale over 6h for adv_id={adv_id_repr}",
                )
            if age > fresh_period:
                return StatsFreshnessState(
                    is_fresh=False,
                    is_stale_over_6h=False,
                    reason=f"{source} stale for adv_id={adv_id_repr}",
                )

        return StatsFreshnessState(is_fresh=True, is_stale_over_6h=False)

    @staticmethod
    def _calc_age(now_utc: datetime, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            normalized = dt.replace(tzinfo=timezone.utc)
        else:
            normalized = dt.astimezone(timezone.utc)
        return now_utc - normalized
