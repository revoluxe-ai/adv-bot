from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, cast
from uuid import UUID

from zoneinfo import ZoneInfo

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.modules.shop_runner.service_manager.services.increment_fact_data_manager.dto.fact_stat_snapshot import FactStatSnapshot
from .fact_stat_repository import FactStatRepository


class FactSalesDeltaManager:
    def __init__(
        self,
        repository: FactStatRepository | None = None,
        tz_name: str = "Europe/Moscow",
    ) -> None:
        self._repository = repository or FactStatRepository(tz_name=tz_name)
        self._tz = ZoneInfo(tz_name)

    async def calculate_fact_data(
        self,
        complex_adv_id: int,
        fact_method: FactMethods,
        nmids: list[int] | None = None,
        *,
        analysis_hours: int = 24,
        projection_hours: int = 24,
    ) -> FactData | None:
        now = datetime.now(self._tz)
        target_ts = now - timedelta(hours=analysis_hours)
        anchor_snapshot: FactStatSnapshot | None = await self._repository.fetch_closest_snapshot(
         complex_adv_id, target_ts
        )
        if anchor_snapshot is None:
            return None

        deltas = await self._repository.aggregate_deltas_between(
        complex_adv_id, anchor_snapshot.src_ts, now
        )
        if not deltas:
            return None

        anchor_ts =anchor_snapshot.src_ts
        period_seconds = max((now - anchor_ts).total_seconds(), 1)
        scale_seconds = projection_hours * 3600

        orders = float(deltas["orders"])
        carts = float(deltas["carts"])
        spend = float(deltas["spend"])

        per_day_orders = orders / period_seconds * scale_seconds
        per_day_carts = carts / period_seconds * scale_seconds
        if fact_method == FactMethods.BY_CARTS:
            ratio = await self._cart_to_order_ratio(nmids, now, 24 * 14)
            predicted_orders = per_day_carts * ratio
        else:
            predicted_orders = per_day_orders

        per_day_spend = spend / period_seconds * scale_seconds
        pay_for_order = per_day_spend / max(predicted_orders, 1)

        return FactData(
            predict_orders=round(predicted_orders, 2),
            original_orders=round(predicted_orders, 2),
            pay_for_order=round(pay_for_order, 2),
            fact_method=fact_method,
        )

    async def _cart_to_order_ratio(
        self,
        nmids: list[int],
        now: datetime,
        analysis_hours: int,
    ) -> float:
        period_days = max(1, math.ceil(analysis_hours / 24))
        end_date = now.date()
        start_date = end_date - timedelta(days=period_days)
        ratio: float = await self._repository.get_carts_to_orders_ratio(
            nmids, start_date, end_date
        )
        return ratio
