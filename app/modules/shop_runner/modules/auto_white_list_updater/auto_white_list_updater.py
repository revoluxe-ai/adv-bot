import datetime

from sqlalchemy import update

from app.modules.common_advs_stat import CommonAdvsStatDataManager
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.full_stat_adv_updater.types.full_adv_stat import SmallFullAdvStatPerDay
from app.utils.db.session_maker import get_async_session_maker as sm
from . import click_house_manager
from .exceptions import AutoUpdateWhiteListFatalError
from .redis_data_manager import MainRedisManager as RedisManager
from ...wb_stat_manager.clickhouse_manager.full_wb_adv_stat import (
    get_daily_stats_by_last_days,
)
from ...wb_statistic_manager.backend import common_stat_manager
from ...wb_statistic_manager.backend.types.common_card_stat import CommonCardStat


class WhiteListUpdateManager:
    """
    Класс отвечает за последовательное удаление ключей из белого списка при перерасходе.

    Работает так:
    1. Проверяет есть ли в редис запись о последней проверке (фикссация суммы)
    1. Берет общие затраты по РК по всем кампания
    1. Проверяет себестоимость заказа за сегодня


    """

    redis_manager = RedisManager()
    _common_stat_data_manager = CommonAdvsStatDataManager()

    async def auto_update_phrases_in_white_list(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> None:
        try:
            return await self._auto_update_phrases_in_white_list(adv, keywords)
        except Exception as exc:
            raise AutoUpdateWhiteListFatalError from exc

    async def _auto_update_phrases_in_white_list(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> None:
        """Основная функция"""

        if not keywords:
            return None
        assert keywords
        keywords.sort(key=lambda kw: kw.predict_ctr, reverse=True)

        first_kw = keywords[0]

        if first_kw.relevant and first_kw.hard_status == 1:
            stmt = (
                update(KeywordSetting)
                .where(KeywordSetting.id == first_kw.keyword_setting_original_id)
                .values({"hard_status": 2})
            )
            async with sm() as session:
                await session.execute(stmt)
                await session.commit()

        auto_adv_id = adv.adv_id
        auction_adv_id = adv.auction_adv_id
        today = datetime.datetime.now()
        all_adv_ids = [auto_adv_id]
        if auction_adv_id:
            all_adv_ids.append(auction_adv_id)
        today_adv_stats: list[SmallFullAdvStatPerDay] = (
            await get_daily_stats_by_last_days(all_adv_ids, today, today)
        )
        if not today_adv_stats:
            raise AutoUpdateWhiteListFatalError("Нет Статистики по рекламе за сегодня ")

        nmid = adv.nmids[0]
        today_common_stats: list[CommonCardStat] | None = (
            await common_stat_manager.get_stats_by_days(nmid, 0)
        )
        if today_common_stats is None:
            raise AutoUpdateWhiteListFatalError("Нет общей статистики за сегодня")

        today_common_stat = today_common_stats[0]
        orders = today_common_stat.orders
        if orders == 0:
            orders = 1

        today_adv_stat = today_adv_stats[0]

        fact_mean_pay_for_order = (
            today_adv_stat.spend / orders
        )  # фактическая максимальная стоимость заказа

        max_pay_for_order = adv.max_price_for_order

        if not max_pay_for_order:
            return None
        if fact_mean_pay_for_order < max_pay_for_order:
            stat_data = await self._common_stat_data_manager.get_data(adv, keywords, 2)
            mean_price_for_order_for_two_days = stat_data.mean_price_for_order
            mean_orders_for_last_two_days: float | None = (
                stat_data.mean_orders_for_last_days
            )
            if (
                mean_orders_for_last_two_days < adv.plan_for_sales_for_day
                and mean_price_for_order_for_two_days < adv.max_price_for_order
            ):
                await self._add_phrase_to_white_list(adv, keywords)
                return None
            elif mean_price_for_order_for_two_days > adv.max_price_for_order:
                await self.__check_spend_and_delete_phrase_from_white_list(
                    adv, keywords
                )
            else:
                return None

        await self.__check_spend_and_delete_phrase_from_white_list(adv, keywords)
        return None

    async def __check_spend_and_delete_phrase_from_white_list(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> None:
        """Проверяет расход и удаляет фразу при необходимости"""
        auto_adv_id = adv.adv_id
        auction_adv_id = adv.auction_adv_id

        # Получаем текущие значения расходов
        last_spend_sum = await self.redis_manager.delete_key_data.get_last_spend_sum(
            auto_adv_id
        )
        sum_spend_now = await click_house_manager.get_sum_spend_for_complex_adv(
            auto_adv_id, auction_adv_id
        )

        # Проверяем условия для удаления
        should_delete = not last_spend_sum or (  # Если нет данных о прошлых расходах
            sum_spend_now - last_spend_sum
        ) >= self._get_max_spend_diff(adv)

        if should_delete:
            await self._delete_last_white_phrase(adv, keywords, sum_spend_now)
        return None

    @staticmethod
    def _get_max_spend_diff(adv: AdvSetting) -> float:
        max_pay_for_order: int = adv.max_price_for_order
        if not max_pay_for_order:
            raise AutoUpdateWhiteListFatalError(
                "Не установлена максимальная стоимость заказа"
            )
        return max_pay_for_order * 0.1

    async def _delete_last_white_phrase(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword], sum_spend_now: float
    ) -> None:

        white_keywords: list[CalculatedKeyword] = [
            kw for kw in keywords if kw.hard_status == 2 and not kw.best_keyword_status
        ]

        if len(white_keywords) <= 1:
            return None

        if not white_keywords:
            return None
        white_keywords.sort(key=lambda kw: kw.baes_ctr, reverse=True)
        down_key: CalculatedKeyword = white_keywords[-1]
        assert down_key
        keyword_setting_original_id: int = down_key.keyword_setting_original_id
        assert keyword_setting_original_id
        async with sm() as session:
            stmt = (
                update(KeywordSetting)
                .values({"hard_status": 1})
                .where(KeywordSetting.id == keyword_setting_original_id)
            )
            await session.execute(stmt)
            await session.commit()
        auto_adv_id = adv.adv_id
        await self.redis_manager.delete_key_data.set_last_spend_sum(
            auto_adv_id, sum_spend_now
        )

        await self.redis_manager.delete_last_datetime.set_last_delete_datetime(adv)

        return None

    async def _add_phrase_to_white_list(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> None:
        keywords_for_adding = [kw for kw in keywords if kw.relevant]
        if not keywords_for_adding:
            return None
        last_adding_phrase_to_white_list = None
        last_views_on_adding_phrase_to_white_list = None
        result: tuple[datetime.datetime, int] | None = (
            await self.redis_manager.adding_key_data.get_last_adding_to_white_list(adv)
        )
        sum_views_from_keywords = sum([kw.views for kw in keywords])
        if result:
            (
                last_adding_phrase_to_white_list,
                last_views_on_adding_phrase_to_white_list,
            ) = result
        if not result or (
            not last_adding_phrase_to_white_list
            or last_views_on_adding_phrase_to_white_list != sum_views_from_keywords
            and last_adding_phrase_to_white_list
            < datetime.datetime.now() - datetime.timedelta(minutes=60)
        ):
            keywords_for_adding.sort(key=lambda kw: kw.predict_ctr, reverse=True)
            keyword_for_adding = keywords_for_adding[0]

            async with sm() as session:
                stmt = (
                    update(KeywordSetting)
                    .where(
                        KeywordSetting.id
                        == keyword_for_adding.keyword_setting_original_id
                    )
                    .values({"hard_status": 2})
                )
                await session.execute(stmt)
                await session.commit()

                now = datetime.datetime.now()

                await self.redis_manager.adding_key_data.set_last_adding_to_white_list(
                    adv, now, sum_views_from_keywords
                )
        return None
