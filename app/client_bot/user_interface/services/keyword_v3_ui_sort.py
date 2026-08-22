"""V3 список ключей в Telegram: enrich CH-профиля для буквы режима (без ladder-sort)."""

from __future__ import annotations

import logging
from typing import cast

from app.client_bot.user_interface.services.keyword_v3_profile_loader import (
    build_complex_adv,
    load_wb_cabinet,
    positions_size_for_adv,
)

# Patch-compatible aliases для unit tests (patch path на этом модуле).
_build_complex_adv = build_complex_adv
_load_wb_cabinet = load_wb_cabinet
_positions_size_for_adv = positions_size_for_adv
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
    merge_position_profiles_from_contexts,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


async def enrich_keywords_v3_list_profiles(
    adv_setting: AdvSetting,
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    """Подставить CH ``position_profile`` в ключи списка для ``keyword_strategy_letter``.

    Сортировка списка — отдельно (``sort_keywords_by_pay_for_order``). Здесь только
    один запрос bid profiles в CH по nmid РК и merge в видимые ключи; без Redis peers
    и без ``fetch_keywords_from_database``.

    Args:
        adv_setting: РК из UI.
        keywords: Отфильтрованные ключи (порядок не меняется).

    Returns:
        Копии с ``position_profile`` где матрица есть в CH; при ошибке — исходный список.
    """
    if not keywords:
        return []

    wb_cabinet = await _load_wb_cabinet(adv_setting.wb_cabinet_id)
    if wb_cabinet is None:
        logger.debug(
            "v3 list enrich: wb_cabinet not found id=%s adv_id=%s",
            adv_setting.wb_cabinet_id,
            adv_setting.adv_id,
        )
        return keywords

    shop_id = wb_cabinet.shop_id
    complex_adv = await _build_complex_adv(adv_setting, shop_id)
    nmids = list(adv_setting.nmids) if adv_setting.nmids else []
    if not nmids:
        return keywords

    nmid = nmids[0]
    positions_size = _positions_size_for_adv(adv_setting)

    try:
        async with await DIManager.create(AppContainer) as container:  # type: ignore[attr-defined]
            factory = cast(
                WBManagerHubFactory,
                container.module_resources.wb_manager_hub_factory_container.wb_manager_hub_factory(),  # pyright: ignore
            )
            hub = factory.get_wb_manager_hub(shop_id)
            min_bids = await hub.wb_manager.get_min_bids_cache_only(
                [complex_adv],
                context="v3_keyword_list_enrich_ui",
            )
    except Exception:
        logger.debug(
            "v3 list enrich: min_bids failed adv_id=%s",
            adv_setting.adv_id,
            exc_info=True,
        )
        return keywords

    min_bid = min_bids.search.get(nmid)
    if min_bid is None:
        logger.debug(
            "v3 list enrich: no min_bid nmid=%s adv_id=%s",
            nmid,
            adv_setting.adv_id,
        )
        return keywords

    try:
        predictor = build_predict_keywords_target_place()
        raw_profiles = await predictor.load_bid_profiles_for_nmid(
            nmid=nmid,
            min_bid=min_bid,
            positions_size=positions_size,
        )
    except Exception:
        logger.debug(
            "v3 list enrich: CH load failed adv_id=%s",
            adv_setting.adv_id,
            exc_info=True,
        )
        return keywords

    contexts = build_keyword_v3_contexts(keywords, raw_profiles)
    if not contexts:
        return keywords

    return merge_position_profiles_from_contexts(keywords, contexts)
