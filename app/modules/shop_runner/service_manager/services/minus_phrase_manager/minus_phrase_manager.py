"""Синхронизация минус-фраз (BAD-ключи) с WB для ``ComplexAdv``.

Контекст для ревью: auto vs search и normquery API
==================================================

Один ``ComplexAdv`` обновляет минус-фразы **параллельно** в двух ветках:

1. **auto** — ``adv_setting`` / ``auto_adv_id`` (в бизнес-языке часто «полка»,
   но технически сюда также относится ``unified`` auto);
2. **search** — ``search_adv`` (аукцион, ``manual`` + search).

WB ``normquery/set-minus`` и ``get-minus`` работают **только** для
``manual + search=true`` (см. ``wb_supports_normquery_minus_phrases``).

Почему skip в auto и search **разный** (намеренно)
--------------------------------------------------

**Search-ветка** (``_update_minuses_in_search_adv``):

- Если после sync meta известна и кампания **не** ``manual+search`` — **skip до API**.
- Search-РК по задумке должна быть аукционом; ранний skip убирает лишние 400.

**Auto-ветка** (``_update_minuses_in_auto_adv``):

- Skip **только** для ``wb_is_manual_shelf_only`` (manual, search=false, rec=true).
- Это закрывает прод-инцидент (полочная auto, adv_id=32824944): WB отклонял
  normquery для такой РК.
- **Не** используем здесь общий ``not wb_supports_normquery_minus_phrases``:
  - ``unified`` auto исторически шли через normquery; миграция на
    ``/adv/v1/auto/set-excluded`` — отдельная задача;
  - редкий ``manual`` без search и без rec — fallback в ``PromotionManager``
    уже возвращает ``skipped_unsupported_campaign`` без raise.

Итог для ревьюера: **ошибки на полочной auto после фикса нет**; search
(``29734515``) продолжает обновляться через normquery. Для прочих auto-типов
возможны warning/400 в логах, но **не** падение shop-runner.

Изоляция ошибок
---------------

- Auto и search — ``asyncio.gather`` без ``return_exceptions``: падение всей
  ветки auto/search валит ``update_minus_phrases`` для ``ComplexAdv``.
- Внутри одной РК по nmid — ``return_exceptions=True`` в ``__update_minus_phrases``.
"""

import asyncio
import logging
from collections.abc import Awaitable

from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.modules.wb_update_state_manager import AdvActiveKeywordUpdateStateManager
from app.shared.domains.wb.utils.wb_campaign_meta import (
    wb_campaign_meta_known,
    wb_is_manual_shelf_only,
    wb_supports_normquery_minus_phrases,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    is_ab_hold_structural_freeze,
)
from .click_house_manager import ClickHouseManager

logger = logging.getLogger(__name__)


class MinusPhraseManager:
    """Обновляет минус-фразы на WB для auto и search кампаний ``ComplexAdv``.

    См. module docstring: различие skip-логики auto (полочная) vs search
    (любая РК без ``manual+search`` при известной meta).
    """

    def __init__(
        self,
        wb_api_manager_hub: WBManagerHub,
        click_house_manager: ClickHouseManager,
        update_redis_timestamp_manager: AdvActiveKeywordUpdateStateManager,
    ):
        self._wb_api = wb_api_manager_hub
        self._click_house = click_house_manager
        self._update_redis_timestamp_manager = update_redis_timestamp_manager

    async def update_minus_phrases(
        self,
        complex_adv: ComplexAdv,
        *,
        force_ab_hold_setup_sync: bool = False,
    ) -> None:
        """Ordinary sync минус-фраз; при A/B Hold freeze — skip (кроме ENTER setup).

        Spec card-ab-hold-mode / decision §8: PENDING/ACTIVE блокируют ordinary
        recalculation. ``force_ab_hold_setup_sync=True`` — одна setup-мутация на ENTER.
        """
        if not force_ab_hold_setup_sync and is_ab_hold_structural_freeze(
            complex_adv.card_ab_hold_mode
        ):
            logger.info(
                "Пропуск ordinary minus recalc (A/B Hold freeze) "
                "shop_id=%s adv_id=%s mode=%s",
                complex_adv.shop_id,
                complex_adv.adv_id,
                complex_adv.card_ab_hold_mode,
            )
            return
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
        """Собрать BAD-ключи и параллельно обновить auto + search ветки."""
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
        """get-minus / set-minus для одной пары (adv_id, nmid) через normquery API.

        Перед записью сравнивает текущий список на WB с целевым. При 400
        «unsupported campaign» fallback возвращает ``skipped_unsupported_campaign``
        — см. ``PromotionManager.set_minus_phrases_with_fallback``.
        """
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
        if getattr(fallback_result, "skipped_unsupported_campaign", False):
            logger.warning(
                "Пропуск normquery set-minus: кампания не поддерживает API "
                "adv_id=%s nmid=%s",
                adv_id,
                nmid,
            )
            return None
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
        """Минус-фразы для auto-РК (``complex_adv.adv_setting``).

        Skip до вызова WB API только для **полочной** auto
        (``wb_is_manual_shelf_only``): ``manual``, search=false, recom=true.

        Почему не ``not wb_supports_normquery_minus_phrases`` как в search:

        - В домене бота «auto» ≈ полка; типичный прод-кейс — именно shelf-only.
        - ``unified`` auto и прочие manual без search пока могут идти в normquery;
          при 400 срабатывает fallback (без exception). Unified — отдельный
          трек на ``/adv/v1/auto/set-excluded``.

        Search-ветка для той же ``ComplexAdv`` работает независимо (parallel gather).
        """
        adv_setting = complex_adv.adv_setting
        if wb_is_manual_shelf_only(adv_setting):
            logger.warning(
                "Пропуск минус-фраз для полочной авто-РК adv_id=%s shop_id=%s",
                complex_adv.auto_adv_id,
                complex_adv.shop_id,
            )
            return None
        adv_id = complex_adv.auto_adv_id
        nmids = adv_setting.nmids
        await self.__update_minus_phrases(adv_id, nmids, bad_keywords)
        return None

    async def _update_minuses_in_search_adv(
        self, complex_adv: ComplexAdv, bad_keywords: list[str]
    ) -> None:
        """Минус-фразы для search/аукционной РК (``complex_adv.search_adv``).

        Если meta синхронизирована и кампания **не** ``manual+search`` — skip до API.
        Это шире, чем skip в auto-ветке: любая search-запись без search placement
        не должна вызывать normquery (WB вернёт 400).

        Легитимный кейс: ``manual`` + ``wb_placement_search=True`` — единственный
        тип, для которого normquery get-minus/set-minus предназначен.
        """
        search_adv = complex_adv.search_adv
        if not search_adv:
            return None
        if wb_campaign_meta_known(search_adv) and not wb_supports_normquery_minus_phrases(
            search_adv
        ):
            logger.warning(
                "Пропуск минус-фраз для поисковой РК без search placement adv_id=%s shop_id=%s",
                search_adv.adv_id,
                complex_adv.shop_id,
            )
            return None
        adv_id = search_adv.adv_id
        nmids = search_adv.nmids
        await self.__update_minus_phrases(adv_id, nmids, bad_keywords)
        return None
