from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.wb_statistic_manager.redis_cluster_stat_timestamp_manager import (
    RedisClusterStatTimestampManager,
)
from app.modules.shop_runner.wb_statistic_manager.redis_common_stat_timestamp_manager import (
    RedisCommonStatTimestampManager,
)
from app.modules.wb_update_state_manager import KeywordStatUpdateState
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
        common_stat_timestamp_manager: RedisCommonStatTimestampManager,
        cluster_stat_timestamp_manager: RedisClusterStatTimestampManager,
    ) -> None:
        self._common_stat_timestamp_manager = common_stat_timestamp_manager
        self._cluster_stat_timestamp_manager = cluster_stat_timestamp_manager
        self._keyword_stat_update_state = KeywordStatUpdateState()

    async def evaluate(self, complex_adv: ComplexAdv) -> StatsFreshnessState:
        now = datetime.now(timezone.utc)
        fresh_period = timedelta(seconds=settings.UPDATE_FULL_ADV_STAT_PERIOD)
        adv_id = complex_adv.adv_id
        keyword_updated_at = await self._keyword_stat_update_state.get_one(adv_id)
        common_updated_at = await self._common_stat_timestamp_manager.get(adv_id)
        cluster_updated_at = await self._cluster_stat_timestamp_manager.get(adv_id)

        keyword_age = self._calc_age(now, keyword_updated_at)
        common_age = self._calc_age(now, common_updated_at)
        cluster_age = self._calc_age(now, cluster_updated_at)

        source_ages = {
            "keyword_stat_update": keyword_age,
            "common_stat_update": common_age,
            "cluster_stat_update": cluster_age,
        }
        for source, age in source_ages.items():
            if age is None:
                return StatsFreshnessState(
                    is_fresh=False,
                    is_stale_over_6h=True,
                    reason=f"{source} missing for adv_id={adv_id}",
                )
            if age > self._EMERGENCY_STALE_PERIOD:
                return StatsFreshnessState(
                    is_fresh=False,
                    is_stale_over_6h=True,
                    reason=f"{source} stale over 6h for adv_id={adv_id}",
                )
            if age > fresh_period:
                return StatsFreshnessState(
                    is_fresh=False,
                    is_stale_over_6h=False,
                    reason=f"{source} stale for adv_id={adv_id}",
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
