import asyncio
import logging
from collections.abc import Awaitable

from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager
from .click_house_manager import ClickHouseManager

logger = logging.getLogger(__name__)


class MinusPhraseManager:
    def __init__(
        self,
        wb_api_manager_hub: WBManagerHub,
        click_house_manager: ClickHouseManager,
        update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager,
    ):
        self._wb_api = wb_api_manager_hub
        self._click_house = click_house_manager
        self._update_redis_timestamp_manager = update_redis_timestamp_manager

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
        bad_keywords: list[str] = [
            kw.text for kw in keywords if kw.status == KeywordStatus.BAD
        ]
        if not bad_keywords:
            return None
        _ = await asyncio.gather(
            self._update_minuses_in_auto_adv(complex_adv, bad_keywords),
            self._update_minuses_in_search_adv(complex_adv, bad_keywords),
        )
        return None

    async def __update_minus_phrases(
        self,
        adv_id: int,
        nmids: list[int],
        common_bad_phrases: list[str],
    ) -> None:
        if not common_bad_phrases:
            return None

        tasks: list[Awaitable[tuple[int, list[str], int] | None]] = []
        for nmid in nmids:
            tasks.append(
                self._sync_minus_phrases_for_nmid(
                    adv_id=adv_id,
                    nmid=nmid,
                    common_bad_phrases=common_bad_phrases,
                )
            )
        if not tasks:
            return None

        results: list[tuple[int, list[str], int] | None | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        for result in results:
            if isinstance(result, BaseException):
                logger.error(
                    "Ошибка обновления РК по nmid для adv_id=%s: %s",
                    adv_id,
                    result,
                    exc_info=(type(result), result, result.__traceback__),
                )
                continue
            if result is None:
                continue
            nmid, dropped_invalid, final_count = result
            if dropped_invalid:
                logger.warning(
                    "Обновление минус-фраз с fallback adv_id=%s nmid=%s "
                    "отброшено=%s итог_фраз=%s",
                    adv_id,
                    nmid,
                    dropped_invalid,
                    final_count,
                )

        return None

    async def _sync_minus_phrases_for_nmid(
        self,
        *,
        adv_id: int,
        nmid: int,
        common_bad_phrases: list[str],
    ) -> tuple[int, list[str], int] | None:
        keywords_from_this_adv_nmid = await self._click_house.get_cluster_texts_for_adv_nmid(
            adv_id, nmid
        )
        bad_keywords_for_nmid = set(common_bad_phrases) & set(keywords_from_this_adv_nmid)
        if not bad_keywords_for_nmid:
            return None

        known_invalid_phrases = set(
            await self._update_redis_timestamp_manager.get_invalid_norm_queries(adv_id, nmid)
        )
        minus_phrases_to_send = sorted(bad_keywords_for_nmid - known_invalid_phrases)[:1000]
        if not minus_phrases_to_send:
            return None
        target_set = set(minus_phrases_to_send)

        current_minus_keywords = await self._wb_api.wb_modifier.get_minus_phrases_for_adv(
            adv_id, nmid
        )
        if set(current_minus_keywords) == target_set:
            return None

        fallback_result = await self._wb_api.wb_modifier.set_minus_phrases_with_fallback_for_adv(
            adv_id=adv_id,
            nmid=nmid,
            phrases=minus_phrases_to_send,
            update_redis_timestamp_manager=self._update_redis_timestamp_manager,
        )
        if fallback_result.dropped_invalid_phrases:
            _ = await self._update_redis_timestamp_manager.add_invalid_norm_queries(
                adv_id=adv_id,
                nmid=nmid,
                phrases=fallback_result.dropped_invalid_phrases,
            )
        return (nmid, fallback_result.dropped_invalid_phrases, len(fallback_result.applied_phrases))

    async def _update_minuses_in_auto_adv(
        self, complex_adv: ComplexAdv, bad_keywords: list[str]
    ) -> None:
        adv_id = complex_adv.auto_adv_id
        nmids = complex_adv.adv_setting.nmids
        await self.__update_minus_phrases(adv_id, nmids, bad_keywords)
        return None

    async def _update_minuses_in_search_adv(
        self, complex_adv: ComplexAdv, bad_keywords: list[str]
    ) -> None:
        search_adv = complex_adv.search_adv
        if not search_adv:
            return None
        adv_id = search_adv.adv_id
        nmids = search_adv.nmids
        await self.__update_minus_phrases(adv_id, nmids, bad_keywords)
        return None
