import datetime

from sqlalchemy import update

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from . import click_house_manager
from .exceptions import AutoUpdateWhiteListFatalError
from .redis_data_manager import RedisManager
from ...wb_stat_manager.clickhouse_manager.full_wb_adv_stat import (
    get_daily_stats_by_last_days,
)
from ...wb_statistic_manager.backend import common_stat_manager
from ...wb_statistic_manager.backend.types.common_card_stat import CommonCardStat


class WhiteListDeleteManager:
    redis_manager = RedisManager()
    """
    Класс отвечает за последовательное удаление ключей из белого списка при перерасходе.

    Работает так:
    1. Проверяет есть ли в редис запись о последней проверке (фикссация суммы )
    1. Берет общие затраты по РК по всем кампания
    1. Проверяет себестоимость заказа за сегодня


    """

    async def auto_delete_phrase_from_white_list(
        self, adv: AdvSetting, keywords: list[CalculatedKeyword]
    ) -> None:
        """Основная функция"""

        auto_adv_id = adv.adv_id
        auction_adv_id = adv.auction_adv_id
        today = datetime.datetime.now()
        all_adv_ids = []
        all_adv_ids.append(auto_adv_id)
        if auction_adv_id:
            all_adv_ids.append(auction_adv_id)
        today_adv_stats: list = await get_daily_stats_by_last_days(
            all_adv_ids, today, today
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

        fact_mean_pay_for_order = today_adv_stat.spend / orders

        max_pay_for_order = adv.max_price_for_order

        if not max_pay_for_order:
            return None

        if not fact_mean_pay_for_order > max_pay_for_order:
            return None

        """Здесь уже есть превышение расхода, нужно проверить прошел ли новый расход для нового ключа"""
        last_spend_sum: float | None = await self.redis_manager.get_last_spend_sum(
            auto_adv_id
        )
        sum_spend_now: float = await click_house_manager.get_sum_spend_for_complex_adv(
            auto_adv_id, auction_adv_id
        )
        if last_spend_sum:
            max_spend_diff: float = self._get_max_spend_diff(adv)

            if sum_spend_now - last_spend_sum < max_spend_diff:
                return None
            else:
                await self._delete_last_white_phrase(adv, keywords, sum_spend_now)
                return None
        else:
            await self._delete_last_white_phrase(adv, keywords, sum_spend_now)
            return None

    @staticmethod
    def _get_max_spend_diff(adv: AdvSetting) -> float:
        max_pay_for_order = adv.max_price_for_order
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

        if not white_keywords:
            return None
        white_keywords.sort(key=lambda kw: kw.baes_ctr, reverse=True)
        down_key: CalculatedKeyword = white_keywords[-1]
        keyword_setting_original_id: int = down_key.keyword_setting_original_id
        assert keyword_setting_original_id
        async with sm() as session:
            stmt = (
                update(KeywordSetting)
                .values({"hard_status": 1})
                .where(KeywordSetting.id == keyword_setting_original_id)
            )
            await session.execute(stmt)
        auto_adv_id = adv.adv_id
        await self.redis_manager.set_last_spend_sum(auto_adv_id, sum_spend_now)
        return None
