import datetime

from sqlalchemy import update

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

from ..setting_auto_updater.data_classes import FactData, PlanData
from . import LastTargetPlaceUpdateRedisManager
from .exc import AutoUpdateTargetPlaceError


class AutoUpdaterTargetPlace:
    def __init__(self, adv: AdvSetting):
        self._adv = adv

    async def update(
        self,
        keywords: list[CalculatedKeyword],
        plan: PlanData,
        fact: FactData,
    ):
        try:
            self._update_target_place(keywords, plan, fact)
        except Exception as exc:
            raise AutoUpdateTargetPlaceError from exc

    @staticmethod
    async def _update_target_place(
        keywords: list[CalculatedKeyword],
        plan: PlanData,
        fact: FactData,
    ) -> None:
        """
        Функция обновляет целевое место в кампании.
        Логика:

        1. Если среднее количество заказов меньше плана, а себестоимость меньше максимальной,
        то повышаем целевое место (1 больше 2)
        2. Если себестоимость выше максимальной, то снижаем место на 1 и т.д.

        Args:
            adv:
            fact_mean_price_for_order_for_last_two_days:
            fact_mean_orders_for_last_two_days:
            keywords:

        Returns:

        """
        if not keywords:
            return None

        redis_manager = LastTargetPlaceUpdateRedisManager(adv)
        last_target_place_update_timestamp: datetime.datetime | None = None
        last_spend: float | None = None
        result: tuple[datetime.datetime, float] | None = (
            await redis_manager.get_last_target_place_update()
        )
        if result:
            last_target_place_update_timestamp, last_spend = result

        now = datetime.datetime.now()
        if (
            last_target_place_update_timestamp
            and spend_sum_from_keywords_now != last_spend
            and now - datetime.timedelta(hours=1) < last_target_place_update_timestamp
        ):
            return None

        current_target_place = adv.max_place
        if fact_mean_price_for_order_for_last_two_days > adv.max_price_for_order:
            new_target_place = current_target_place + 1
        else:
            if fact_mean_orders_for_last_two_days < adv.plan_for_sales_for_day:
                new_target_place = current_target_place - 1
            else:
                if fact_mean_price_for_order_for_last_two_days > adv.target_price_for_order:
                    new_target_place = current_target_place + 1
                else:
                    return None
        if new_target_place < 1:
            new_target_place = 1

        if new_target_place == current_target_place:
            return None

        stmt = update(AdvSetting).where(AdvSetting.id == adv.id).values(max_place=new_target_place)
        timestamp = datetime.datetime.now()
        async with sm(read_only=False) as session:
            await session.execute(stmt)
            await session.commit()
        await redis_manager.set_last_target_place_update(
            adv, timestamp, spend_sum_from_keywords_now
        )
        return None
