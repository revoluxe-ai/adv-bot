import asyncio
import logging
from collections.abc import Awaitable
from app.core.mp.wb.api.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from .click_house_manager import ClickHouseManager

logger = logging.getLogger(__name__)


class MinusPhraseManager:
    def __init__(self, wb_api_manager_hub: WBManagerHub,
                 click_house_manager: ClickHouseManager):
        self._wb_api = wb_api_manager_hub
        self._click_house = click_house_manager

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

    async def _update_minus_phrases(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        bad_keywords: list[str] = [kw.text for kw in keywords if kw.status==KeywordStatus.BAD]
        await asyncio.gather(
            self._update_minuses_in_auto_adv(complex_adv, bad_keywords),
            self._update_minuses_in_search_adv(complex_adv, bad_keywords)
        )
        return None

    async def __update_minus_phrases(self,
                                     adv_id: int,
                                     nmids: list[int],
                                     common_bad_phrases: list[str]) -> None:
        keywords_from_this_adv: list[str] = await self._get_clusters_for_adv(adv_id)

        bad_keywords_for_this_adv = set(common_bad_phrases) & set(keywords_from_this_adv)
        if not bad_keywords_for_this_adv:
            return None

        minus_phrases_to_send = list(bad_keywords_for_this_adv)[:1000]

        tasks: list[Awaitable[None]] = []
        for nmid in nmids:
            task = self._wb_api.wb_modifier.set_minus_phrases_for_adv(
            adv_id=adv_id,
            nmid=nmid,
            phrases=minus_phrases_to_send,
        )
            tasks.append(task)

        results: list[None | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error('Ошибка обновления РК: %s', result, exc_info=True)


        return None

    async def _get_clusters_for_adv(self, adv_id: int) -> list[str]:
        keywords: list[str] = await self._click_house.get_cluster_texts_for_adv(adv_id)
        return keywords

    async def _update_minuses_in_auto_adv(self, complex_adv: ComplexAdv, bad_keywords: list[str]) -> None:
        adv_id = complex_adv.auto_adv_id
        nmids = complex_adv.adv_setting.nmids
        await self.__update_minus_phrases(adv_id, nmids, bad_keywords)
        return None


    async def _update_minuses_in_search_adv(self, complex_adv: ComplexAdv, bad_keywords: list[str]) -> None:
        adv_id = complex_adv.search_adv.adv_id
        nmids = complex_adv.search_adv.nmids
        await self.__update_minus_phrases(adv_id, nmids, bad_keywords)
        return None
