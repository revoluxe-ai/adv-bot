import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast
from . import clickhouse_manager
from sqlalchemy import select
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_stat_manager.leg_cpo import compute_leg_cpo
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import (
    CommonCardStat,
)

from app.utils.db.session_maker import get_async_session_maker
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

_sm = get_async_session_maker


# TODO: Переделать NEO4j Драйвер на DI с нормальным управлением ЖЦ


@dataclass
class CommonAdvsStatData:
    """Класс для хранения данных о ключевых словах рекламной кампании"""

    adv_setting: AdvSetting
    keywords: list[CalculatedKeyword]
    min_orders_per_1000_rub: float | None
    hard_min_ctr: float | None
    auto_cpm: int
    auction_cpm: int | None
    total_spend: float
    addition_spend_in_adv: float
    all_orders_for_last_days: float | None
    mean_orders_for_last_days: float | None
    mean_price_for_order: float | None
    spend_for_inner_advs: float | None
    full_adv_stat_for_last_days_for_auto_adv: SmallFullAdvStat
    full_adv_stat_for_last_days_for_auction: SmallFullAdvStat
    common_stat: CommonCardStat | None
    sales_predict_method: FactMethods
    cost_per_order_from_additional_last_week: float | None
    auto_cpo: float | None = None
    search_cpo: float | None = None
    stat_start_date: datetime | None = None
    stat_end_date: datetime | None = None


class CommonAdvsStatDataManager:
    """Менеджер для получения данных о ключевых словах рекламной кампании"""

    @staticmethod
    async def _fetch_auction_cpm_if_any(adv_setting: AdvSetting) -> int | None:
        search_adv_id = adv_setting.search_adv_id
        if not search_adv_id:
            return None
        stmt = select(AdvSetting.cpm).where(AdvSetting.adv_id == search_adv_id)
        async with _sm() as session:
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_data(
        self, adv_setting: AdvSetting, keywords: list[CalculatedKeyword], last_days: int
    ) -> CommonAdvsStatData:
        """Получает все необходимые данные для отображения информации о ключевых словах"""

        auction_cpm: int | None = await self._fetch_auction_cpm_if_any(adv_setting)

        pass_days = last_days - 1
        end_date = datetime.now()
        start_date = end_date - timedelta(days=pass_days)

        auto_adv_id = int(adv_setting.adv_id)
        search_adv_id = (
            int(adv_setting.search_adv_id)
            if adv_setting.search_adv_id is not None
            else None
        )
        leg_adv_ids = [auto_adv_id]
        if search_adv_id is not None:
            leg_adv_ids.append(search_adv_id)
        stats_by_adv_id = await full_wb_adv_stat.get_stats_by_adv_ids_last_days(
            leg_adv_ids,
            start_date,
            end_date,
        )
        empty_stat = SmallFullAdvStat(0, 0, 0.0, 0, 0, 0.0)
        full_adv_stat_for_last_days_for_auto_adv = stats_by_adv_id.get(
            auto_adv_id, empty_stat
        )
        full_adv_stat_for_last_days_for_auction = (
            stats_by_adv_id.get(search_adv_id, empty_stat)
            if search_adv_id is not None
            else empty_stat
        )

        # Общий расход
        full_spend_for_all_advs = (
            full_adv_stat_for_last_days_for_auto_adv.spend
            + full_adv_stat_for_last_days_for_auction.spend
        )

        common_stat: CommonCardStat | None = (
            await common_stat_manager.get_stats_for_last_period(
                int(adv_setting.nmids[0]), pass_days
            )
        )
        # Legacy runtime уже безусловно читает orders/add_to_cart ниже. Cast только
        # фиксирует существующий contract для strict typing, не меняя failure semantics.
        common_stat_required = cast(CommonCardStat, common_stat)

        # Рассчитываем дополнительные метрики
        all_orders_from_advs = (
            full_adv_stat_for_last_days_for_auto_adv.orders
            + full_adv_stat_for_last_days_for_auction.orders
        )

        # Проверяем источник заказов для автоуправления
        if adv_setting.orders_source_for_auto_mode == OrdersSourceForAutoMode.ADV_SUM:
            # Используем только заказы из рекламы (Авто + Аукцион)
            base_common_orders = all_orders_from_advs
            spend_for_inner_advs_for_days = full_spend_for_all_advs
        elif (
            adv_setting.orders_source_for_auto_mode
            == OrdersSourceForAutoMode.COMMON_STATISTIC
        ):
            # Используем общую статистику (по умолчанию)
            base_common_orders = common_stat_required.orders
            if base_common_orders < all_orders_from_advs:
                base_common_orders = all_orders_from_advs
            spend_for_inner_advs_for_days = full_spend_for_all_advs
        else:
            raise NotImplementedError(
                f"Неизвестный источник заказов для автоуправления: {adv_setting.orders_source_for_auto_mode}"
            )
        # TODO: Тут надо изменить логику получения данных для прогноза, пока делаю заглушку: небольшое число,
        #  показывающее что корзин или заказов мало,
        #  хотя их нет вообще. Варианты как решить задачу тут docks/forecast_strategy.md
        if base_common_orders == 0:
            base_common_orders = 0.06
        base_common_carts: float = common_stat_required.add_to_cart
        # TODO: Здесь ошибка ушла в прод, нужно сделать тест, сделал HOT-FIX, проверить логику
        if base_common_carts == 0:
            base_common_carts = 0.2
        predict_orders_for_days = await self._get_predict_orders_for_day(
            adv_setting, base_common_orders, base_common_carts,
        )

        # Исправлено: используем реальные заказы вместо прогнозируемых с дробной частью дня
        # для корректного расчета средней себестоимости заказа
        mean_price_for_order = (
            spend_for_inner_advs_for_days / max(base_common_orders, 1)
        )

        (
            spend_for_keywords_in_auto_adv,
            cost_per_order_from_additional_last_week,
        ) = await asyncio.gather(
            full_wb_adv_stat.get_keywords_spend(
                [adv_setting.adv_id], start_date, end_date
            ),
            full_wb_adv_stat.get_additional_cost_per_order_for_adv(
                adv_setting.adv_id, days=7
            ),
        )

        addition_spend_in_adv = (
            full_adv_stat_for_last_days_for_auto_adv.spend
            - spend_for_keywords_in_auto_adv
        )

        from app.modules.wb_adv_updater import phrases_processor
        min_orders_per_1000_rub: float | None = phrases_processor.get_min_orders_per_1000_rub(
            keywords
        )
        return CommonAdvsStatData(
            adv_setting=adv_setting,
            keywords=keywords,
            min_orders_per_1000_rub=min_orders_per_1000_rub,
            hard_min_ctr=adv_setting.hard_min_ctr,
            auto_cpm=adv_setting.cpm,
            auction_cpm=auction_cpm, # TODO: вот это похоже на depricated, надо выпилить
            total_spend=full_spend_for_all_advs,
            addition_spend_in_adv=addition_spend_in_adv,
            all_orders_for_last_days=base_common_orders,
            mean_orders_for_last_days=predict_orders_for_days,
            mean_price_for_order=mean_price_for_order,
            spend_for_inner_advs=spend_for_inner_advs_for_days,
            full_adv_stat_for_last_days_for_auto_adv=full_adv_stat_for_last_days_for_auto_adv,
            full_adv_stat_for_last_days_for_auction=full_adv_stat_for_last_days_for_auction,
            common_stat=common_stat,
            sales_predict_method=adv_setting.sales_predict_method,
            cost_per_order_from_additional_last_week=cost_per_order_from_additional_last_week,
            auto_cpo=compute_leg_cpo(stats_by_adv_id.get(auto_adv_id)),
            search_cpo=(
                compute_leg_cpo(stats_by_adv_id.get(search_adv_id))
                if search_adv_id is not None
                else None
            ),
            stat_start_date=start_date,
            stat_end_date=end_date,
        )

    async def _get_predict_orders_for_day(
        self,
        adv: AdvSetting,
        base_common_orders: float,
        base_common_carts: float,

    ) -> float:
        # TODO: Переделать вычисление, где будет не только конвертация в корзину, но и
        if adv.sales_predict_method == FactMethods.DIRECT_SALES:
            return base_common_orders
        elif adv.sales_predict_method == FactMethods.BY_CARTS:
            basket_to_order_ratio: float = await self._get_cart_to_order_ratio(adv)
            base_predict_orders = base_common_carts / basket_to_order_ratio
            return base_predict_orders
        else:
            raise NotImplementedError(
                f"Неизвестный метод прогноза заказов: {adv.sales_predict_method}"
            )
    @staticmethod
    async def _get_cart_to_order_ratio(
    adv: AdvSetting, pass_days: int = 7
    ) -> float:
        ch = clickhouse_manager
        ratio = await ch.get_cart_to_order_ratio_from_common_items_stat(adv, pass_days)
        if not ratio:
            # TODO: Ошибка в прод ушла = сделать тест
            ratio = 1.0
        return ratio
    @staticmethod
    def _get_predict_order_for_fractation_day(
        base_predict_orders: float, pass_days: int
    ) -> float:
        now = datetime.now()
        hours_passed = now.hour + now.minute / 60 + now.second / 3600
        fraction_of_day = hours_passed / 24 + pass_days
        predict_orders_for_days = base_predict_orders / fraction_of_day
        return predict_orders_for_days
