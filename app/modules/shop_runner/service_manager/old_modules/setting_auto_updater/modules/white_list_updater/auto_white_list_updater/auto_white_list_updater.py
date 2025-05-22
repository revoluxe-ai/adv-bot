from typing import TypeVar

from sqlalchemy import update

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
    KeywordStatus,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.utils.db.session_maker import get_async_session_maker as sm
from .redis_cache.redis_cache import AdvSettingRedisCache

T = TypeVar("T")
import logging

logger = logging.getLogger(__name__)


# def raise_exception() -> (
#     Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]
# ):
#     def decorator(
#         func: Callable[..., Awaitable[T]],
#     ) -> Callable[..., Awaitable[T]]:
#         @wraps(func)
#         async def wrapper(*args: Any, **kwargs: Any) -> T:
#             try:
#                 return await func(*args, **kwargs)
#             except Exception as e:
#                 logger.error(
#                     f"Ошибка корутины: {func.__name__}. Ошибка: {e}", exc_info=True
#                 )
#                 raise AutoUpdateWhiteListFatalError from e
#
#         return wrapper
#
#     return decorator


#
# def _get_max_spend_diff(adv: AdvSetting) -> float:
#     max_pay_for_order: int = adv.max_price_for_order
#     if not max_pay_for_order:
#         raise AutoUpdateWhiteListFatalError(
#             "Не установлена максимальная стоимость заказа"
#         )
#     return max_pay_for_order * 0.1
#


class WhiteListUpdateManager:
    """
    Класс отвечает за последовательное удаление ключей из белого списка при перерасходе.

    Работает так:
    1. Проверяет есть ли в редис запись о последней проверке (фикссация суммы)
    1. Берет общие затраты по РК по всем кампания
    1. Проверяет себестоимость заказа за сегодня


    """

    def __init__(self, adv: AdvSetting):
        self._adv = adv
        self.redis_cache = AdvSettingRedisCache(adv)

    async def delete_last_white_phrase(
        self,
        keywords: list[CalculatedKeyword],
    ) -> tuple[bool, bool]:
        redis_cache = self.redis_cache
        pass_time = 60 * 15
        if not await redis_cache.last_auto_delete_white_list.check_pass_time(pass_time):
            return False, False

        white_keywords: list[CalculatedKeyword] = [
            kw for kw in keywords if kw.hard_status == 2 and not kw.best_keyword_status
        ]
        white_keywords.sort(key=lambda kw: kw.baes_ctr, reverse=True)
        white_keywords = white_keywords[1:]
        if not white_keywords:
            return False, True
        down_key: CalculatedKeyword = white_keywords[-1]
        assert down_key
        assert down_key.keyword_setting_original_id
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
        await redis_cache.last_auto_delete_white_list.set()
        return True, False

    async def add_phrase_to_white_list(
        self, keywords: list[CalculatedKeyword]
    ) -> tuple[bool, bool]:
        redis_cache = self.redis_cache
        pass_time = 60 * 15
        if not await redis_cache.last_auto_adding_phrase_to_white_list.check_pass_time(
            pass_time
        ):
            return False, False

        def candidate_for_white_list_filter(keyword: CalculatedKeyword) -> bool:
            if (
                keyword.relevant
                and keyword.hard_status == 1
                and keyword.status == KeywordStatus.BAD
            ):
                return True
            else:
                return False

        keywords_for_adding = list(filter(candidate_for_white_list_filter, keywords))
        if not keywords_for_adding:
            return False, True

        keywords_for_adding.sort(key=lambda kw: kw.rating_by_predict_ctr, reverse=True)
        keyword_for_adding = keywords_for_adding[0]

        async with sm() as session:
            stmt = (
                update(KeywordSetting)
                .where(
                    KeywordSetting.id == keyword_for_adding.keyword_setting_original_id
                )
                .values({"hard_status": 2})
            )
            await session.execute(stmt)
            await session.commit()
            await redis_cache.last_auto_adding_phrase_to_white_list.set()
            return True, False
