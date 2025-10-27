from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStat
from app.modules.shop_runner.wb_stat_manager.clickhouse_manager import full_wb_adv_stat
from app.modules.shop_runner.wb_statistic_manager.backend import common_stat_manager
from app.modules.shop_runner.wb_statistic_manager.backend.types.common_card_stat import (
    CommonCardStat,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker


@dataclass
class CommonAdvsStatData:
    """Класс для хранения данных о ключевых словах рекламной кампании"""

    adv_setting: AdvSetting
    keywords: list[CalculatedKeyword]
    min_ctr: float
    auto_cpm: int
    auction_cpm: int | None
    total_spend: float
    addition_spend_in_adv: float
    all_orders_for_last_days: int | None
    mean_orders_for_last_days: float | None
    mean_price_for_order: float | None
    spend_for_inner_advs: float | None
    full_adv_stat_for_last_days_for_auto_adv: SmallFullAdvStat
    full_adv_stat_for_last_days_for_auction: SmallFullAdvStat
    common_stat: CommonCardStat | None


class CommonAdvsStatDataManager:
    """Менеджер для получения данных о ключевых словах рекламной кампании"""

    @classmethod
    async def get_data(
        cls,
        adv_setting: AdvSetting, keywords: list[CalculatedKeyword], last_days: int
    ) -> CommonAdvsStatData:
        """
        Получает все необходимые данные с учетом флага use_incremental_stats.
        
        Если флаг включен - используем инкрементальные таблицы (новая логика).
        Если выключен - используем дневные агрегаты (старая логика).
        """
        # Проверяем флаг использования инкрементальной статистики
        if adv_setting.use_incremental_stats:
            # НОВАЯ ЛОГИКА: используем инкрементальные таблицы
            return await cls._get_data_from_incremental(
                adv_setting, keywords, hours=1
            )
        else:
            # СТАРАЯ ЛОГИКА: используем дневные агрегаты (как раньше)
            return await cls._get_data_from_legacy(
                adv_setting, keywords, last_days
            )

    @classmethod
    async def _get_data_from_legacy(
        cls,
        adv_setting: AdvSetting, keywords: list[CalculatedKeyword], last_days: int
    ) -> CommonAdvsStatData:
        """СТАРАЯ ЛОГИКА: Получает данные из дневных агрегатов с экстраполяцией"""

        # Получаем min_ctr
        min_ctr = await data_manager.get_min_ctr(adv_setting)

        # Получаем CPM для аукциона
        auction_cpm = None
        if search_adv_id := adv_setting.search_adv_id:
            stmt = select(AdvSetting.cpm).where(AdvSetting.adv_id == search_adv_id)
            async with _sm() as session:
                result = await session.execute(stmt)
                auction_cpm = result.scalar_one_or_none()

        pass_days = last_days - 1
        end_date = datetime.now()
        start_date = end_date - timedelta(days=pass_days)

        # Статистика для авто-рекламы
        full_adv_stat_for_last_days_for_auto_adv = (
            await full_wb_adv_stat.get_stats_by_last_days(
                [adv_setting.adv_id], start_date, end_date
            )
        )

        # Статистика для аукциона
        if adv_setting.search_adv_id:
            full_adv_stat_for_last_days_for_auction = (
                await full_wb_adv_stat.get_stats_by_last_days(
                    [adv_setting.search_adv_id], start_date, end_date
                )
            )
        else:
            # Пустая статистика, если нет search_adv_id
            full_adv_stat_for_last_days_for_auction = SmallFullAdvStat(views=0, clicks=0, spend=0.0, added_to_cart=0, orders=0, sum_price=0)

        # Общий расход
        full_spend_for_all_advs = (
            full_adv_stat_for_last_days_for_auto_adv.spend
            + full_adv_stat_for_last_days_for_auction.spend
        )

        # Общая статистика
        common_stat: (
            CommonCardStat | None
        ) = await common_stat_manager.get_stats_for_last_period(
            int(adv_setting.nmids[0]), pass_days
        )

        # Рассчитываем дополнительные метрики
        base_common_orders: int | None = None
        all_orders_from_advs = (
            full_adv_stat_for_last_days_for_auto_adv.orders
            + full_adv_stat_for_last_days_for_auction.orders
        )
        mean_orders_for_days = None
        mean_price_for_order = None
        spend_for_inner_advs_for_days = None

        # Проверяем источник заказов для автоуправления
        if adv_setting.orders_source_for_auto_mode == OrdersSourceForAutoMode.ADV_SUM:
            # Используем только заказы из рекламы (Авто + Аукцион)
            base_common_orders = int(all_orders_from_advs)
            if base_common_orders == 0:
                base_common_orders = 1
            spend_for_inner_advs_for_days = full_spend_for_all_advs

            now = datetime.now()
            hours_passed = now.hour + now.minute / 60 + now.second / 3600
            fraction_of_day = hours_passed / 24 + pass_days

            mean_orders_for_days = base_common_orders / fraction_of_day
            mean_price_for_order = spend_for_inner_advs_for_days / base_common_orders
        elif common_stat:
            # Используем общую статистику (по умолчанию)
            base_common_orders = int(common_stat.orders)
            if base_common_orders < int(all_orders_from_advs):
                base_common_orders = int(all_orders_from_advs)
            if base_common_orders == 0:
                base_common_orders = 1
            spend_for_inner_advs_for_days = full_spend_for_all_advs

            now = datetime.now()
            hours_passed = now.hour + now.minute / 60 + now.second / 3600
            fraction_of_day = hours_passed / 24 + pass_days

            mean_orders_for_days = base_common_orders / fraction_of_day
            mean_price_for_order = spend_for_inner_advs_for_days / base_common_orders

        # Получаем расходы на ключевые слова
        spend_for_keywords_in_auto_adv = await full_wb_adv_stat.get_keywords_spend(
            [adv_setting.adv_id], start_date, end_date, "advkeyword"
        )

        addition_spend_in_adv = (
            full_adv_stat_for_last_days_for_auto_adv.spend
            - spend_for_keywords_in_auto_adv
        )

        return CommonAdvsStatData(
            adv_setting=adv_setting,
            keywords=keywords,
            min_ctr=min_ctr,
            auto_cpm=adv_setting.cpm,
            auction_cpm=auction_cpm,
            total_spend=full_spend_for_all_advs,
            addition_spend_in_adv=addition_spend_in_adv,
            all_orders_for_last_days=int(base_common_orders) if base_common_orders is not None else None,
            mean_orders_for_last_days=mean_orders_for_days,
            mean_price_for_order=mean_price_for_order,
            spend_for_inner_advs=spend_for_inner_advs_for_days,
            full_adv_stat_for_last_days_for_auto_adv=full_adv_stat_for_last_days_for_auto_adv,
            full_adv_stat_for_last_days_for_auction=full_adv_stat_for_last_days_for_auction,
            common_stat=common_stat,
        )

    @classmethod
    async def _get_data_from_incremental(
        cls,
        adv_setting: AdvSetting, keywords: list[CalculatedKeyword], hours: int
    ) -> CommonAdvsStatData:
        """
        НОВАЯ ЛОГИКА: Получает данные на основе инкрементальных записей.
        
        Использует точные данные за период без экстраполяции на сутки.
        Стабильно работает в течение дня, не "колбасит".
        
        Args:
            adv_setting: Настройки РК
            keywords: Ключевые слова
            hours: Период анализа в часах (например, 24)
        """
        from app.modules.shop_runner.wb_statistic_manager.backend.incremental_stat_manager import (
            IncrementalCommonStatManager,
            IncrementalAdvStatManager,
        )

        # Получаем min_ctr
        min_ctr = await data_manager.get_min_ctr(adv_setting)

        # Получаем CPM для аукциона
        auction_cpm = None
        if search_adv_id := adv_setting.search_adv_id:
            stmt = select(AdvSetting.cpm).where(AdvSetting.adv_id == search_adv_id)
            async with _sm() as session:
                result = await session.execute(stmt)
                auction_cpm = result.scalar_one_or_none()

        # Инициализируем менеджеры
        common_manager = IncrementalCommonStatManager()
        adv_manager = IncrementalAdvStatManager()

        # Собираем общую статистику по артикулу из инкрементальных дельт
        nmid = int(adv_setting.nmids[0])
        orders_total = await common_manager.get_total_for_period(nmid, hours, "orders")
        orders_sum_total = await common_manager.get_total_for_period(nmid, hours, "orders_sum")
        open_card_total = await common_manager.get_total_for_period(nmid, hours, "open_card")
        add_to_cart_total = await common_manager.get_total_for_period(nmid, hours, "add_to_cart")
        buy_outs_total = await common_manager.get_total_for_period(nmid, hours, "buy_outs")

        # Создаём объект (как в старой логике, но данные из дельт)
        common_stat = CommonCardStat(
            nmid=nmid,
            open_card=int(open_card_total),
            add_to_cart=int(add_to_cart_total),
            orders=int(orders_total),
            orders_sum=float(orders_sum_total),
            buy_outs=int(buy_outs_total),
        )
        common_stat.date = datetime.now().date()

        # Заказы за последние N часов (уже получили в common_stat)
        all_orders_for_period = orders_total

        # Расходы из рекламы
        adv_ids = [adv_setting.adv_id]
        if adv_setting.search_adv_id:
            adv_ids.append(adv_setting.search_adv_id)

        total_spend = await adv_manager.get_total_for_period(adv_ids, hours, "spend")
        auto_adv_spend = await adv_manager.get_total_for_period(
            [adv_setting.adv_id], hours, "spend"
        )
        auction_spend = await adv_manager.get_total_for_period(
            [adv_setting.search_adv_id] if adv_setting.search_adv_id else [],
            hours,
            "spend",
        )

        auto_adv_orders = await adv_manager.get_total_for_period(
            [adv_setting.adv_id], hours, "orders"
        )
        auction_orders = await adv_manager.get_total_for_period(
            [adv_setting.search_adv_id] if adv_setting.search_adv_id else [],
            hours,
            "orders",
        )

        all_orders_from_advs = auto_adv_orders + auction_orders

        # Рассчитываем метрики
        base_common_orders: int | None = None
        mean_orders_for_days = None
        mean_price_for_order = None
        spend_for_inner_advs_for_days = None

        if adv_setting.orders_source_for_auto_mode == OrdersSourceForAutoMode.ADV_SUM:
            # Используем только заказы из рекламы
            base_common_orders = int(all_orders_from_advs)
            if base_common_orders == 0:
                base_common_orders = 1
            spend_for_inner_advs_for_days = total_spend

            # Среднее за час → экстраполируем на день
            mean_orders_per_hour = (int(all_orders_from_advs) / hours) if hours > 0 else 0
            mean_orders_for_days = mean_orders_per_hour * 24

            mean_price_for_order = total_spend / base_common_orders
        else:
            # Используем общую статистику
            base_common_orders = int(common_stat.orders)
            if base_common_orders < int(all_orders_from_advs):
                base_common_orders = int(all_orders_from_advs)
            if base_common_orders == 0:
                base_common_orders = 1
            spend_for_inner_advs_for_days = total_spend

            # Среднее за час → экстраполируем на день
            mean_orders_per_hour = (base_common_orders / hours) if hours > 0 else 0
            mean_orders_for_days = mean_orders_per_hour * 24

            mean_price_for_order = total_spend / base_common_orders

        # Создаем заглушки для SmallFullAdvStat (для совместимости с интерфейсом)
        full_adv_stat_for_last_days_for_auto_adv = SmallFullAdvStat(
            views=0,
            clicks=0,
            spend=auto_adv_spend,
            added_to_cart=0,
            orders=int(auto_adv_orders),
            sum_price=0,
        )

        full_adv_stat_for_last_days_for_auction = SmallFullAdvStat(
            views=0,
            clicks=0,
            spend=auction_spend,
            added_to_cart=0,
            orders=int(auction_orders),
            sum_price=0,
        )

        # Расходы на ключевые слова
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours)
        spend_for_keywords_in_auto_adv = await full_wb_adv_stat.get_keywords_spend(
            [adv_setting.adv_id], start_date, end_date, "advkeyword"
        )

        addition_spend_in_adv = auto_adv_spend - spend_for_keywords_in_auto_adv

        return CommonAdvsStatData(
            adv_setting=adv_setting,
            keywords=keywords,
            min_ctr=min_ctr,
            auto_cpm=adv_setting.cpm,
            auction_cpm=auction_cpm,
            total_spend=total_spend,
            addition_spend_in_adv=addition_spend_in_adv,
            all_orders_for_last_days=int(base_common_orders) if base_common_orders is not None else None,
            mean_orders_for_last_days=mean_orders_for_days,
            mean_price_for_order=mean_price_for_order,
            spend_for_inner_advs=spend_for_inner_advs_for_days,
            full_adv_stat_for_last_days_for_auto_adv=full_adv_stat_for_last_days_for_auto_adv,
            full_adv_stat_for_last_days_for_auction=full_adv_stat_for_last_days_for_auction,
            common_stat=common_stat,  # Используем common_stat из инкрементальных данных
        )
