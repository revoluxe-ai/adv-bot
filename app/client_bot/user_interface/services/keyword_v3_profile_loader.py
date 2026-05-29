"""Загрузка профиля ставок CH для карточки ключа V3 в Telegram."""

from __future__ import annotations

import logging
from dataclasses import replace
from typing import cast

from sqlalchemy import select

from app.client_bot.user_interface.views.keyword_v3_profile_ui import KeywordV3ProfileData
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
    RedisCalculatedKeywordsCacheManager,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
    load_campaign_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_eligibility_map,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    cache_worst_costs_for_adv,
    has_campaign_worst_costs,
    ladder_view_to_candidates,
    resolve_ladder_stage_display,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_worst_costs_cache import (
    V3WorstCostsRedisCache,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    diagnose_keyword_v3_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    resolve_keyword_v2_pay_for_order_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

_DEFAULT_POSITIONS_SIZE = 300
_MAX_POSITIONS_SIZE = 300  # как в ``PredictKeywordsTargetPlace.load_bid_profiles_for_nmid``


async def _load_wb_cabinet(wb_cabinet_id: int) -> WBCabinet | None:
    """Кабинет по id без lazy-load от detached ``AdvSetting``."""
    stmt = select(WBCabinet).where(WBCabinet.id == wb_cabinet_id)
    async with sm(read_only=True) as session:
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def _redis_keywords_for_complex_adv(
    complex_adv: ComplexAdv,
    *,
    cache_only: bool = False,
) -> list[CalculatedKeyword] | None:
    """Ключи РК из Redis — для ``load_campaign_v3_contexts`` в карточке Telegram.

    ``cache_only=False`` не пересчитывает V2 в UI (только кеш).
    """
    _ = cache_only
    return await RedisCalculatedKeywordsCacheManager().get_all_calculated_keywords_for_adv(
        complex_adv.adv_id
    )


async def _build_complex_adv(adv_setting: AdvSetting, shop_id: str) -> ComplexAdv:
    """Собрать ``ComplexAdv`` с провайдером ключей (нужен для peer pool лестницы)."""
    search_adv = None
    search_adv_id = adv_setting.search_adv_id
    if search_adv_id:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            search_adv = result.scalar_one_or_none()
    return ComplexAdv(
        adv_setting=adv_setting,
        search_adv=search_adv,
        shop_id=shop_id,
        get_keywords_func=_redis_keywords_for_complex_adv,
    )


def _positions_size_for_adv(adv_setting: AdvSetting) -> int:
    """Размер профиля позиций для CH; не больше лимита предиктора (300)."""
    if adv_setting.min_target_position is None:
        return _DEFAULT_POSITIONS_SIZE
    size = int(adv_setting.min_target_position)
    if size > _MAX_POSITIONS_SIZE:
        logger.warning(
            "v3 keyword profile: min_target_position=%s > %s for adv_id=%s, clamping",
            size,
            _MAX_POSITIONS_SIZE,
            adv_setting.adv_id,
        )
        return _MAX_POSITIONS_SIZE
    if size < 1:
        logger.warning(
            "v3 keyword profile: min_target_position=%s < 1 for adv_id=%s, using 1",
            size,
            adv_setting.adv_id,
        )
        return 1
    return size


def _empty_n_state_candidates() -> dict[AggressionTargetMode, ModeCandidate]:
    """Пустая лестница для N-state (нет матрицы CH)."""
    return {
        m: ModeCandidate(
            mode=m,
            is_valid=False,
            invalid_reason="no_position_profile",
        )
        for m in AggressionTargetMode
    }


def _keyword_profile_metrics(
    calculated_keyword: CalculatedKeyword,
) -> tuple[float | None, float | None]:
    """CTR факт ключа и показ→заказ V2 для блока профиля лестницы."""
    stat = calculated_keyword.cluster_stat
    ctr = calculated_keyword.ctr if stat.views > 0 else None
    conv_order = calculated_keyword.conv_views_to_orders
    if conv_order <= 0:
        return ctr, None
    return ctr, float(conv_order)


def _profile_fields_from_diagnostic(
    calculated_keyword: CalculatedKeyword,
    diagnostic: object,
    *,
    keyword_ctr: float | None = None,
    conv_views_to_orders: float | None = None,
    worst_costs: dict | None = None,
) -> dict[str, object]:
    """Общие поля ``KeywordV3ProfileData`` из диагностики ключа."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
        KeywordV3DataDiagnostic,
    )

    assert isinstance(diagnostic, KeywordV3DataDiagnostic)
    return {
        "n_state": diagnostic.n_state,
        "no_ch_min_only": diagnostic.no_ch_min_only,
        "diagnostic": diagnostic,
        "keyword_ctr": keyword_ctr,
        "conv_views_to_orders": conv_views_to_orders,
        "v2_pay_for_order": resolve_keyword_v2_pay_for_order_cost(
            calculated_keyword, worst_costs=worst_costs
        ),
        "keyword_pay_for_order": _keyword_pay_for_order_field(calculated_keyword),
    }


def _keyword_pay_for_order_field(
    calculated_keyword: CalculatedKeyword,
) -> float | None:
    """Себест. заказа из карточки ключа для UI NO CH tier."""
    pfo = calculated_keyword.pay_for_order
    if pfo is None or float(pfo) <= 0:
        return None
    return float(pfo)


def profile_load_failure(
    calculated_keyword: CalculatedKeyword,
    *,
    reason: str,
) -> KeywordV3ProfileData:
    """Технический сбой загрузки WB/CH с диагностикой V2/CH по статистике ключа."""
    diagnostic = diagnose_keyword_v3_data(calculated_keyword, None)
    return KeywordV3ProfileData(
        current_mode=calculated_keyword.strategy_mode,
        candidates=_empty_n_state_candidates(),
        load_failure=reason,
        **_profile_fields_from_diagnostic(calculated_keyword, diagnostic),
    )


async def load_keyword_v3_profile_data(
    adv_setting: AdvSetting,
    calculated_keyword: CalculatedKeyword,
) -> KeywordV3ProfileData | None:
    """Профиль лестницы для одного ключа: SSOT ``resolve_ladder_stage_display``.

    Returns:
        Данные для UI или ``None``, если WB/CH контекст недоступен.
    """
    wb_cabinet = await _load_wb_cabinet(adv_setting.wb_cabinet_id)
    if wb_cabinet is None:
        logger.warning(
            "v3 keyword profile: wb_cabinet not found id=%s adv_id=%s",
            adv_setting.wb_cabinet_id,
            adv_setting.adv_id,
        )
        return profile_load_failure(calculated_keyword, reason="нет кабинета WB")

    shop_id = wb_cabinet.shop_id
    complex_adv = await _build_complex_adv(adv_setting, shop_id)
    nmids = list(adv_setting.nmids) if adv_setting.nmids else []
    if not nmids:
        return profile_load_failure(calculated_keyword, reason="нет nmid у кампании")
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
                context="v3_keyword_profile_ui",
            )
    except Exception:
        logger.exception(
            "v3 keyword profile: min_bids load failed adv_id=%s keyword=%s",
            adv_setting.adv_id,
            calculated_keyword.text,
        )
        return profile_load_failure(
            calculated_keyword, reason="ошибка загрузки min bid WB"
        )

    min_bid = min_bids.search.get(nmid)
    if min_bid is None:
        logger.warning(
            "v3 keyword profile: no min_bid in cache nmid=%s adv_id=%s",
            nmid,
            adv_setting.adv_id,
        )
        return profile_load_failure(calculated_keyword, reason="min bid не в кеше WB")

    try:
        predictor = build_predict_keywords_target_place()
        raw_profiles = await predictor.load_bid_profiles_for_nmid(
            nmid=nmid,
            min_bid=min_bid,
            positions_size=positions_size,
        )
    except Exception:
        logger.exception(
            "v3 keyword profile: CH load failed adv_id=%s keyword=%s",
            adv_setting.adv_id,
            calculated_keyword.text,
        )
        return profile_load_failure(calculated_keyword, reason="ошибка запроса CH")

    all_contexts = await load_campaign_v3_contexts(complex_adv, raw_profiles)
    if not all_contexts:
        single = build_keyword_v3_contexts([calculated_keyword], raw_profiles)
        all_contexts = single if single else []
    ladder_inputs = LadderInputs.from_contexts(all_contexts)
    if not ladder_inputs.worst_costs:
        cached_worst = await V3WorstCostsRedisCache().get_worst_costs(
            adv_setting.adv_id
        )
        if cached_worst:
            ladder_inputs = replace(ladder_inputs, worst_costs=cached_worst)
    await cache_worst_costs_for_adv(adv_setting.adv_id, ladder_inputs.worst_costs)
    has_worst = has_campaign_worst_costs(ladder_inputs.worst_costs)

    bids = resolve_keyword_bid_profile(raw_profiles, calculated_keyword.text)
    profile_points = (
        profile_points_from_bid_positions(bids) if bids else None
    )
    ctx = KeywordV3Context(
        keyword=calculated_keyword.model_copy(
            update={"position_profile": profile_points}
        ),
        position_profile=profile_points,
    )
    diagnostic = diagnose_keyword_v3_data(
        calculated_keyword,
        profile_points,
        peer_contexts=all_contexts,
    )
    keyword_ctr, conv_views_to_orders = _keyword_profile_metrics(calculated_keyword)

    if (
        diagnostic.n_state
        and not diagnostic.no_ch_min_only
        and not diagnostic.has_ch_position_profile
        and not has_worst
    ):
        return KeywordV3ProfileData(
            current_mode=calculated_keyword.strategy_mode,
            candidates=_empty_n_state_candidates(),
            **_profile_fields_from_diagnostic(
                calculated_keyword,
                diagnostic,
                keyword_ctr=keyword_ctr,
                conv_views_to_orders=conv_views_to_orders,
                worst_costs=ladder_inputs.worst_costs,
            ),
        )

    eligibility_map = build_eligibility_map(all_contexts)
    ks_id = calculated_keyword.keyword_setting_original_id
    elig = (
        eligibility_map.get(int(ks_id)) if ks_id is not None else None
    )
    ladder = resolve_ladder_stage_display(ctx, ladder_inputs, eligibility=elig)
    candidates = ladder_view_to_candidates(ladder)
    stage_sources = {
        mode: ladder.stages[mode].source.value for mode in ladder.stages
    }

    campaign_worst_only = (
        not diagnostic.has_ch_position_profile
        and has_worst
        and not diagnostic.no_ch_min_only
    )
    fields = _profile_fields_from_diagnostic(
        calculated_keyword,
        diagnostic,
        keyword_ctr=keyword_ctr,
        conv_views_to_orders=conv_views_to_orders,
        worst_costs=ladder_inputs.worst_costs,
    )
    fields["n_state"] = bool(fields["n_state"]) and not has_worst
    return KeywordV3ProfileData(
        current_mode=calculated_keyword.strategy_mode,
        candidates=candidates,
        campaign_worst_only=campaign_worst_only,
        campaign_worst_costs=dict(ladder_inputs.worst_costs),
        stage_sources=stage_sources,
        **fields,
    )
