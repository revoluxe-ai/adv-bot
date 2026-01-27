from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Generator, Protocol, Sequence, TypeVar, cast
from typing_extensions import ParamSpec

from sqlalchemy import select


from app.settings import settings
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from .dto.keyword_hard_status import KeywordHardStatus
from .dto.states import KeywordStatus, KeywordStatusReason
from .keyword_stat import KeywordStat
from app.core.clickhouse_manager import BaseClickHouseManager
from app.core.clikhouse_client_manager import  get_clickhouse_client
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.pre_calculated_keyword import PreCalculatedKeyword
from ...calculated_keywords_redis_cache_manager.redis_manager import RedisCalculatedKeywordsCacheManager
from ...common_slaves.wildberries.models import KeywordSetting
from app.utils.db.session_maker import  get_async_session_maker as sm
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from operator import  attrgetter
from cashews import cache, noself  # pyright: ignore


import typing

if typing.TYPE_CHECKING:
    from ...shop_runner.service_manager.wb_shop_data_manager import ComplexAdv


P = ParamSpec("P")
R = TypeVar("R")


class _AsyncDecoratorFactory(Protocol):
    def __call__(
        self, *, ttl: str, lock: bool
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        ...


def _typed_noself_cache() -> _AsyncDecoratorFactory:
    """Typed wrapper for ``cashews.noself(cache)``.

    cashews doesn't ship strict typings for this decorator factory.
    This helper preserves the signature of decorated async callables
    for pyright/mypy.
    """

    return cast(Any, noself(cache))


class _ClickHouseNamedResultsResponse(Protocol):
    def named_results(self) -> Generator[dict[str, int | float | str], None, None]:
        ...



# TODO: Нужно сделать автоматизацию по проверке обновлений API и внесением правок через ИИ


class CalculatedKeywordsManager(BaseClickHouseManager):
    async def get_calculated_keywords(self,
                                      complex_adv: 'ComplexAdv',
                                      min_days: int=7,
                                      min_views: int=500) \
            -> list[CalculatedKeyword]:
        # TODO: Сделать на будущее более глобальные объекты для списков, в котором будут передаваться не только данные, но и метаданные
        # TODO: тут получаем только для одного артикула, возможно, что нал
        results = await asyncio.gather(
            self._get_all_keyword_setting(complex_adv),
            self._get_all_stats(complex_adv, min_days, min_views),
        )
        keyword_hard_statuses:  list[KeywordHardStatus] = list(results[0])
        stats = results[1]

        pre_calculated_keywords = self.__create_pre_calculated_keywords(keyword_hard_statuses,
                                                                        stats,
                                                                        complex_adv)
        if not pre_calculated_keywords:
            return []
        calculated_keyword_list = await self.__get_calculated_keywords(complex_adv, pre_calculated_keywords)
        await self._set_calculated_keywords_in_redis_cache(complex_adv, calculated_keyword_list)

        return calculated_keyword_list

    async def _get_all_stats(self, complex_adv: 'ComplexAdv', min_days: int, min_views: int):
        nmids = complex_adv.nmids
        return await self._get_keywords_stat_from_clickhouse(nmids, min_days, min_views)

    async def _get_keywords_stat_from_clickhouse(self,
                                                  nmids: list[int],
                                                  min_days: int,
                                                  min_views: int,
                                                  cart_to_order_window:int=14
                                                  ) -> list[KeywordStat]:
        """Fetch keyword statistics from ClickHouse and parse them into models.

        This is a higher-level wrapper around
        ``__get_keywords_stat_from_clickhouse``. It forwards the query
        parameters to the cached low-level ClickHouse call and converts the
        raw dictionaries returned from ClickHouse into ``KeywordStat`` model
        instances.

        Args:
            nmids: List of Wildberries product IDs (nmids) to fetch statistics
                for. A list is used so that statistics for multiple products
                can be retrieved in a single ClickHouse query.
            min_days: Minimum number of days of statistics that must be
                available for a keyword to be included in the result.
            min_views: Minimum number of views required for a keyword to be
                included in the result set.
            cart_to_order_window: Number of days to use as the conversion
                window when aggregating cart-to-order statistics.

        Returns:
            A list of ``KeywordStat`` objects with aggregated statistics for
            the requested nmids that satisfy the specified filters.

        Note:
            This method itself is not cached. Caching is applied at the level
            of ``__get_keywords_stat_from_clickhouse``, which is decorated
            with ``@noself(cache)`` and caches the raw ClickHouse query
            results for a short period.
        """
        result: list[dict[str, int | float | str]] = await self.__get_keywords_stat_from_clickhouse(
            nmids, min_days, min_views, cart_to_order_window
        )
        stats: list[KeywordStat] = []
        for obj in result:
            stat = KeywordStat.model_validate(obj)
            stats.append(stat)
        return stats

    @_typed_noself_cache()(ttl="15m", lock=True)
    async def __get_keywords_stat_from_clickhouse(self,
                                                  nmids: list[int],
                                                  min_days: int,
                                                  min_views: int,
                                                  cart_to_order_window:int=14
                                                  ) -> list[dict[str, int | float | str]]:
        query = self._get_query('get_clusters_stats')

        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "nmids": nmids,
                        "min_views": min_views,
                        "min_days": min_days,
                        "conv_days": cart_to_order_window,
                    },
                )

        typed_response = cast(_ClickHouseNamedResultsResponse, response)
        result: Generator[dict[str, int | float | str], None, None] = typed_response.named_results()
        return list(result)



    @staticmethod
    def __create_pre_calculated_keywords(keyword_hard_statuses: list[KeywordHardStatus],
                                               stats: list[KeywordStat],
                                               complex_adv: 'ComplexAdv') \
            -> list[PreCalculatedKeyword]:
        from .convertor import  keyword_setting_to_keyword_setting_dto
        text_to_stat = {stat.text: stat for stat in stats}
        keywords: list[PreCalculatedKeyword] = []
        for keyword_hard_status in keyword_hard_statuses:
            keyword_setting = keyword_hard_status.keyword_setting
            stat = text_to_stat.get(keyword_setting.text)
            if stat:
                keyword_setting_dto = keyword_setting_to_keyword_setting_dto(keyword_setting)
                calculated_keyword = PreCalculatedKeyword(
                    keyword_setting=keyword_setting_dto,
                    cluster_stat=stat,
                    adv_id=complex_adv.adv_id,
                    bidder_status=keyword_hard_status.bidder_keyword_status
                )
                keywords.append(calculated_keyword)
        return keywords

    async def _get_all_keyword_setting(self, complex_adv: 'ComplexAdv') -> list[KeywordHardStatus]:
        adv_setting_original_id = complex_adv.original_adv_setting_id
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_original_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()

        texts: list[str] = [kw.text for kw in keyword_settings]
        keyword_hard_statuses_map = await self._get_bidder_keyword_statuses(complex_adv, texts)
        keyword_hard_statuses: list[KeywordHardStatus] = []
        for keyword_setting in keyword_settings:
            keyword_hard_statuses.append(KeywordHardStatus(
                keyword_setting=keyword_setting,
                bidder_keyword_status=keyword_hard_statuses_map[keyword_setting.text]
            ))
        return keyword_hard_statuses

    @staticmethod
    async def __get_calculated_keywords(complex_adv: 'ComplexAdv',
                                        pre_keywords: list[PreCalculatedKeyword]) -> list[CalculatedKeyword]:
        calculated_keyword_list: list[CalculatedKeyword] = []
        from .dto.inner_dto.keyword_state import KeywordState
        white_list = [kw for kw in pre_keywords if kw.hard_status == 2]
        if not white_list:
            """Если нет белого списка, режем по заданному CTR-у"""
            hard_min_ctr  = complex_adv.hard_min_ctr
            if hard_min_ctr is None:
                min_ctr = settings.DEFAULT_MIN_CTR
            else:
                min_ctr = hard_min_ctr
            best_keyword = max(pre_keywords, key=attrgetter("ctr"))
            for pre_kw in pre_keywords:
                best_keyword_status = True if pre_kw == best_keyword else False
                if pre_kw.bidder_status == BidderKeywordStatus.BAD:
                    state = KeywordState(
                        status=KeywordStatus.BAD,
                        reason=KeywordStatusReason.BIDDER_BAD_STATUS,
                        best_keyword_status=best_keyword_status
                    )
                elif pre_kw.ctr >= min_ctr:
                    state = KeywordState(
                        status=KeywordStatus.GOOD,
                        reason=KeywordStatusReason.MORE_THEN_HARD_MIN_CTR,
                        best_keyword_status=best_keyword_status)
                else:
                    status = KeywordStatus.BAD
                    reason = KeywordStatusReason.LESS_THEN_HARD_MIN_CTR
                    state = KeywordState(
                        status=status,
                        reason=reason,
                        best_keyword_status=best_keyword_status)
                calculated_keyword = CalculatedKeyword(
                    adv_id=pre_kw.adv_id,
                    keyword_setting=pre_kw.keyword_setting,
                    cluster_stat=pre_kw.cluster_stat,
                    state=state,
                 target_pay_for_order=complex_adv.target_pay_for_order,)
                calculated_keyword_list.append(calculated_keyword)
            return calculated_keyword_list

        """Основной алгоритм"""
        white_list.sort(key=lambda kw: kw.rating_by_orders)
        best_keyword = max(pre_keywords, key=attrgetter("rating_by_orders"))
        worst_keyword = white_list[0]
        rating_by_orders_of_worst_keyword = worst_keyword.rating_by_orders
        for pre_kw in pre_keywords:
            best_keyword_status = True if pre_kw == best_keyword else False
            hard_status = pre_kw.hard_status
            if hard_status == 3:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.TURN_OFF
                best_keyword_status = True if pre_kw==best_keyword else False
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status
                )
            elif hard_status == 2:
                status = KeywordStatus.GOOD
                reason = KeywordStatusReason.WHITE_LIST
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status
                )
            elif hard_status == 0:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.BLACK_LIST
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status
                )
            elif pre_kw.rating_by_orders >= rating_by_orders_of_worst_keyword:
                status = KeywordStatus.GOOD
                reason = KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
                state = KeywordState(status=status,
                                     reason=reason,
                                     best_keyword_status=best_keyword_status)
            else:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
                state = KeywordState(status=status,
                                     reason=reason,
                                     best_keyword_status=best_keyword_status)

            calculated_keyword_list.append(CalculatedKeyword(adv_id=pre_kw.adv_id,
                                                         keyword_setting=pre_kw.keyword_setting,
                                                         cluster_stat=pre_kw.cluster_stat,
                                                         state=state,
                                                         target_pay_for_order=complex_adv.target_pay_for_order
                                                         ))
        return calculated_keyword_list


    @staticmethod
    async def _set_calculated_keywords_in_redis_cache(complex_adv: 'ComplexAdv',
                                                      calculated_keyword_list: list[CalculatedKeyword]) -> None:
        redis_cache_manager = RedisCalculatedKeywordsCacheManager()
        await redis_cache_manager.set_calculated_keywords(calculated_keyword_list, complex_adv.adv_id)

    @staticmethod
    async def _get_bidder_keyword_statuses(complex_adv: 'ComplexAdv',
                                           texts: list[str]) -> dict[str, BidderKeywordStatus]:
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        # КОСТЫЛЬ: Пробуем получить из контекста, если не получается - создаем на лету
        try:
            wb_manager_hub = WBManagerHubFactory.get_wb_manager_from_context()
        except RuntimeError:
            # Если контекст не установлен (например, в боте), создаем на лету
            from app.core.di.client_di.wb_manager_hub_container import WBManagerHubContainer
            from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
            from app.core.redis_manager_v2.redis_client import RedisClient
            from app.configs import AppConfig
            from redis.asyncio import Redis

            # Создаем Redis клиент напрямую (костыль)
            config = AppConfig.create()
            redis_config = config.infrastructure.redis
            raw_redis_client = Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=True,
            )
            redis_client_wrapper = RedisClient(redis_client=raw_redis_client)
            httpx_client_handler = HttpxClientHandler()

            # Создаем контейнер и получаем hub
            wb_manager_hub_container = WBManagerHubContainer(
                _shop_id=complex_adv.shop_id,
                _httpx_client_handler=httpx_client_handler,
                _redis_wrapper=redis_client_wrapper,
            )
            wb_manager_hub = wb_manager_hub_container.wb_manager_hub()

        redis_manager_instance = wb_manager_hub.redis_keyword_bidder_status_manager

        statuses_map: dict[str, BidderKeywordStatus] = await redis_manager_instance.get_statuses(  # pyright: ignore
            complex_adv, texts
        )
        return statuses_map
