"""Сортировка списка ключей V3 в Telegram UI по state_cost (SSOT ladder + CH)."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import cast

from app.client_bot.user_interface.services.keyword_v3_profile_loader import (
    _build_complex_adv,
    _load_wb_cabinet,
    _positions_size_for_adv,
)
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_eligibility_map,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    cache_worst_costs_for_adv,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_worst_costs_cache import (
    V3WorstCostsRedisCache,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.sort_utils import (
    pay_for_order_sort_key,
    sort_keywords_by_current_state_cost,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


async def sort_keywords_for_v3_ui(
    adv_setting: AdvSetting,
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword]:
    """Отсортировать ключи для клавиатуры V3: state_cost текущего режима (OFF → MIN).

    При недоступности CH/min_bids — fallback на ``pay_for_order`` asc (прежнее UI).

    Args:
        adv_setting: РК из UI.
        keywords: Уже отфильтрованный список ключей.

    Returns:
        Отсортированная копия списка.
    """
    if not keywords:
        return []

    wb_cabinet = await _load_wb_cabinet(adv_setting.wb_cabinet_id)
    if wb_cabinet is None:
        logger.warning(
            "v3 ui sort: wb_cabinet not found id=%s adv_id=%s, fallback pay_for_order",
            adv_setting.wb_cabinet_id,
            adv_setting.adv_id,
        )
        return sorted(keywords, key=pay_for_order_sort_key)

    shop_id = wb_cabinet.shop_id
    complex_adv = await _build_complex_adv(adv_setting, shop_id)
    nmids = list(adv_setting.nmids) if adv_setting.nmids else []
    if not nmids:
        logger.warning(
            "v3 ui sort: no nmid adv_id=%s, fallback pay_for_order",
            adv_setting.adv_id,
        )
        return sorted(keywords, key=pay_for_order_sort_key)

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
                context="v3_keyword_list_sort_ui",
            )
    except Exception:
        logger.warning(
            "v3 ui sort: min_bids load failed adv_id=%s, fallback pay_for_order",
            adv_setting.adv_id,
            exc_info=True,
        )
        return sorted(keywords, key=pay_for_order_sort_key)

    min_bid = min_bids.search.get(nmid)
    if min_bid is None:
        logger.warning(
            "v3 ui sort: no min_bid nmid=%s adv_id=%s, fallback pay_for_order",
            nmid,
            adv_setting.adv_id,
        )
        return sorted(keywords, key=pay_for_order_sort_key)

    try:
        predictor = build_predict_keywords_target_place()
        raw_profiles = await predictor.load_bid_profiles_for_nmid(
            nmid=nmid,
            min_bid=min_bid,
            positions_size=positions_size,
        )
    except Exception:
        logger.warning(
            "v3 ui sort: CH load failed adv_id=%s, fallback pay_for_order",
            adv_setting.adv_id,
            exc_info=True,
        )
        return sorted(keywords, key=pay_for_order_sort_key)

    contexts = build_keyword_v3_contexts(keywords, raw_profiles)
    if not contexts:
        return sorted(keywords, key=pay_for_order_sort_key)

    from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
        load_campaign_orders_per_cart_7d,
        load_rec_orders_per_view_for_v3,
    )

    campaign_orders_per_cart_7d = await load_campaign_orders_per_cart_7d(adv_setting)
    rec_orders_per_view = await load_rec_orders_per_view_for_v3(
        adv_setting,
        rec_system_promotion_mode_active=complex_adv.rec_system_promotion_mode_active,
    )
    ladder_inputs = LadderInputs.from_contexts(
        contexts,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        rec_orders_per_view=rec_orders_per_view,
    )
    if not ladder_inputs.worst_costs:
        cached_worst = await V3WorstCostsRedisCache().get_worst_costs(adv_setting.adv_id)
        if cached_worst:
            ladder_inputs = replace(ladder_inputs, worst_costs=cached_worst)
    await cache_worst_costs_for_adv(adv_setting.adv_id, ladder_inputs.worst_costs)

    eligibility_by_ks_id = build_eligibility_map(
        contexts,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
    )
    return sort_keywords_by_current_state_cost(
        keywords,
        contexts,
        ladder_inputs,
        eligibility_by_ks_id,
    )
