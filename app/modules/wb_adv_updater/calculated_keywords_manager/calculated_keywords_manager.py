import asyncio
from typing import Generator, Protocol, Sequence, cast
from sqlalchemy import select

from app.settings import settings
from .dto.states import KeywordStatus, KeywordStatusReason
from .keyword_stat import KeywordStat
from app.core.clickhouse_manager import BaseClickHouseManager
from app.core.clikhouse_client_manager import  get_clickhouse_client
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.pre_calculated_keyword import PreCalculatedKeyword
from ...calculated_keywords_redis_cache_manager.redis_manager import RedisCalculatedKeywordsCacheManager
from ...common_slaves.wildberries.models import KeywordSetting
from ...shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.utils.db.session_maker import  get_async_session_maker as sm
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from operator import  attrgetter

class _ClickHouseNamedResultsResponse(Protocol):
    def named_results(self) -> Generator[dict[str, int | float | str], None, None]:
        ...



# TODO: Нужно сделать автоматизацию по проверке обновлений API и внесением правок через ИИ


class CalculatedKeywordsManager(BaseClickHouseManager):


    async def get_calculated_keywords(self, complex_adv: ComplexAdv, min_days: int=7, min_views: int=500) \
            -> list[CalculatedKeyword]:
        # TODO: Сделать на будущее более глобальные объекты для списков, в котором будут передаваться не только данные, но и метаданные
        # TODO: тут получаем только для одного артикула, возможно, что нал
        results = await asyncio.gather(self._get_all_keyword_setting(complex_adv),
                                       self._get_all_stats(complex_adv, min_days, min_views),
                                 )
        keyword_settings = list(results[0])
        stats = results[1]
        pre_calculated_keywords = await self.__create_pre_calculated_keywords(keyword_settings, stats, complex_adv)
        if not pre_calculated_keywords:
            return []
        calculated_keywords = await self.__get_calculated_keywords(complex_adv, pre_calculated_keywords)
        await self._set_calculated_keywords_in_redis_cache(complex_adv, calculated_keywords)

        return calculated_keywords

    async def _get_all_stats(self, complex_adv: ComplexAdv, min_days: int, min_views: int):
        get_stat_tasks = [self.__get_keywords_stat_from_clickhouse(nmid, min_days, min_views)
                          for nmid in complex_adv.nmids]

        results: list[list[KeywordStat]] = await asyncio.gather(*get_stat_tasks)
        stats: list[KeywordStat] = []
        for result in results:
            stats.extend(result)
        return stats

    async def __get_keywords_stat_from_clickhouse(self,
                                                  nmid: int,
                                                  min_days: int,
                                                  min_views: int,
                                                  cart_to_order_window:int=14
                                                  ) -> list[KeywordStat]:
        query = self._get_query('get_clusters_stats')


        async with get_clickhouse_client() as client:
            response = await client.query(
                query,
                parameters={
                    "nmid": nmid,
                    "min_views": min_views,
                    "min_days": min_days,
                    "conv_days": cart_to_order_window,
                },
            )

        typed_response = cast(_ClickHouseNamedResultsResponse, response)
        result: Generator[dict[str, int | float | str], None, None] = typed_response.named_results()
        stats: list[KeywordStat] = []
        for obj in result:
            stat = KeywordStat.model_validate(obj)
            stats.append(stat)
        return stats

    @staticmethod
    async def __create_pre_calculated_keywords(keyword_settings: list[KeywordSetting],
                                               stats: list[KeywordStat],
                                               complex_adv: ComplexAdv) -> list[PreCalculatedKeyword]:
        from .convertor import  keyword_setting_to_keyword_setting_dto
        text_to_stat = {stat.text: stat for stat in stats}
        keywords: list[PreCalculatedKeyword] = []
        for keyword_setting in keyword_settings:
            stat = text_to_stat.get(keyword_setting.text)
            if stat:
                keyword_setting_dto = keyword_setting_to_keyword_setting_dto(keyword_setting)
                calculated_keyword = PreCalculatedKeyword(
                    keyword_setting=keyword_setting_dto,
                    cluster_stat=stat,
                    adv_id=complex_adv.adv_id,
                )
                keywords.append(calculated_keyword)
        return keywords

    @staticmethod
    async def _get_all_keyword_setting(complex_adv: ComplexAdv) -> Sequence[KeywordSetting]:
        adv_setting_original_id = complex_adv.original_adv_setting_id
        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_original_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()
        return keyword_settings


    @staticmethod
    async def __get_calculated_keywords(complex_adv: ComplexAdv,
                                        pre_keywords: list[PreCalculatedKeyword]) -> list[CalculatedKeyword]:
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
            calculated_keywords: list[CalculatedKeyword] = []
            for pre_kw in pre_keywords:
                best_keyword_status = True if pre_kw == best_keyword else False
                if pre_kw.ctr >= min_ctr:
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
                    state=state)
                calculated_keywords.append(calculated_keyword)
            return calculated_keywords

        """Основной алгоритм"""
        white_list.sort(key=lambda kw: kw.rating_by_orders)
        best_keyword = max(pre_keywords, key=attrgetter("rating_by_orders"))
        worst_keyword = white_list[0]
        rating_by_orders_of_worst_keyword = worst_keyword.rating_by_orders
        calculated_keywords: list[CalculatedKeyword] = []
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
            calculated_keywords.append(CalculatedKeyword(adv_id=pre_kw.adv_id,
                                                         keyword_setting=pre_kw.keyword_setting,
                                                         cluster_stat=pre_kw.cluster_stat,
                                                         state=state))
        return calculated_keywords

    @staticmethod
    async def _set_calculated_keywords_in_redis_cache(complex_adv: ComplexAdv,
                                                      calculated_keywords: list[CalculatedKeyword]) -> None:
        redis_cache_manager = RedisCalculatedKeywordsCacheManager()
        await redis_cache_manager.set_calculated_keywords(calculated_keywords, complex_adv.adv_id)













