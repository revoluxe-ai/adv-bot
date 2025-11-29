import asyncio
import logging
from collections.abc import Awaitable
from typing import cast

from app.core.mp.wb.api.adapter.promotion_client.normquery_stats import NormqueryStatsDTO
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    KeywordStatus,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)

logger = logging.getLogger(__name__)


class MinusPhraseManager:
    def __init__(self, wb_api_manager_hub: WBManagerHub):
        self._wb_api = wb_api_manager_hub

    async def update_minus_phrases(self, complex_adv: ComplexAdv) -> None:
        try:
            await self._update_minus_phrases(complex_adv)
        except Exception as e:
            logger.error(
                "Ошибка обновления минус фраз для shop_id: %s, adv_id: %s, ошибка: %s",
                complex_adv.shop_id,
                complex_adv.adv_id,
                e,
                exc_info=True,
            )
            raise e

    async def _get_norm_query_from_stat(self, complex_adv: ComplexAdv, last_days: int) -> list[str]:
        """TODO: Временный метод, заменить на записи из кликхауса"""
        tasks: list[Awaitable[list[NormqueryStatsDTO]]] = []
        nmid = complex_adv.main_nmid
        # if adv_id := complex_adv.auto_adv_id:
        #     task: Awaitable[list[NormqueryStatsDTO]] = self._wb_api.wb_data_manager.get_norn_query_stat(adv_id,
        #                                                                   nmid,
        #                                                                       last_days)
        #     tasks.append(task)
        if complex_adv.search_adv:
            adv_id = complex_adv.search_adv.adv_id
            task: Awaitable[list[NormqueryStatsDTO]] = self._wb_api.wb_data_manager.get_norn_query_stat(adv_id,
                                                                              nmid,
                                                                                 last_days)
            tasks.append(task)

        results: list[list[NormqueryStatsDTO] | BaseException] = await asyncio.gather(*tasks,
                                                                                  return_exceptions=True)
        norm_queries: set[str] = set()
        for result in results:
            if isinstance(result, Exception):
                logger.error('Ошибка получения norm query: %s', result)
            else:
                result = cast(list[NormqueryStatsDTO], result)
                for stat in result:
                    query: str = stat.norm_query
                    norm_queries.add(query)
        return list(norm_queries)


    async def _update_minus_phrases(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        bad_phrases = [
            kw.text for kw in keywords if kw.status == KeywordStatus.BAD
        ]

        norm_queries = await self._get_norm_query_from_stat(complex_adv, last_days=7)

        bad_norm_queries = set(bad_phrases) &  set(norm_queries)

        if not bad_norm_queries:
            logger.debug(
                "Нет минус фраз для обновления для shop_id: %s, adv_id: %s",
                complex_adv.shop_id,
                complex_adv.adv_id,
            )
            return

        # API лимит - 1000 фраз. Берем только "плохие"
        minus_phrases_to_send = list(bad_norm_queries)[:1000]

        await self._wb_api.wb_modifier.set_minus_phrases_for_adv(
            complex_adv=complex_adv,
            phrases=minus_phrases_to_send,
        )

        logger.debug(
            "Минус-фразы успешно обновлены для shop_id: %s, adv_id: %s, фразы: %s",
            complex_adv.shop_id,
            complex_adv.adv_id,
            minus_phrases_to_send,
        )
