"""Загрузка профиля ставок CH для карточки ключа V3 в Telegram."""

from __future__ import annotations

import logging
from typing import TypedDict, cast

from sqlalchemy import select

from app.client_bot.user_interface.views.keyword_v3_profile_ui import KeywordV3ProfileData
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
    load_campaign_v3_contexts_from_database,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    resolve_keyword_v2_pay_for_order_cost,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_eligibility_map,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    ladder_view_to_candidates,
    resolve_ladder_stage_display,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    KeywordV3DataDiagnostic,
    diagnose_keyword_v3_data,
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


async def _ui_get_keywords_from_redis(
    complex_adv: ComplexAdv,
    *,
    cache_only: bool = True,
) -> list[CalculatedKeyword]:
    """Провайдер ``ComplexAdv.get_keywords`` для Telegram UI (strict Redis).

    Args:
        complex_adv: РК с ``shop_id`` и ``adv_id``.
        cache_only: Должен быть ``True``; пересчёт из БД в UI — ``fetch_keywords_from_database``.

    Returns:
        Keywords из ``calculated_keywords:{adv_id}``.

    Raises:
        ShopRunnerKeywordsCacheMissError: hash/meta в Redis отсутствуют.
    """
    if not cache_only:
        raise RuntimeError(
            "_ui_get_keywords_from_redis(cache_only=False) отключён в UI: "
            "используйте fetch_keywords_from_database()."
        )
    from app.modules.shop_runner.required_data_miss import (
        fetch_calculated_keywords_from_redis,
    )

    return await fetch_calculated_keywords_from_redis(
        complex_adv.adv_id,
        shop_id=complex_adv.shop_id or "",
    )


async def _build_complex_adv(adv_setting: AdvSetting, shop_id: str) -> ComplexAdv:
    """Собрать ``ComplexAdv`` для UI: peers лестницы — Redis ``get_keywords``, список/карточка — БД отдельно."""
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
        get_keywords_func=_ui_get_keywords_from_redis,
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
    """Conv показ→корзина и показ→заказ ключа для блока профиля лестницы."""
    stat = calculated_keyword.cluster_stat
    conv_cart: float | None = None
    if stat.views > 0 and calculated_keyword.add_to_cart >= 0:
        conv_cart = float(calculated_keyword.add_to_cart) / float(stat.views)
    conv_order = calculated_keyword.conv_views_to_orders
    if conv_order <= 0:
        return conv_cart, None
    return conv_cart, float(conv_order)


class _ProfileDiagnosticFields(TypedDict):
    """Поля ``KeywordV3ProfileData``, общие для N-state / failure / full ladder."""

    n_state: bool
    no_ch_min_only: bool
    diagnostic: KeywordV3DataDiagnostic
    conv_views_to_cart: float | None
    conv_views_to_orders: float | None
    v2_pay_for_order: float | None
    keyword_pay_for_order: float | None


def _profile_fields_from_diagnostic(
    calculated_keyword: CalculatedKeyword,
    diagnostic: KeywordV3DataDiagnostic,
    *,
    conv_views_to_cart: float | None = None,
    conv_views_to_orders: float | None = None,
    worst_costs: dict[AggressionTargetMode, float] | None = None,
) -> _ProfileDiagnosticFields:
    """Общие поля ``KeywordV3ProfileData`` из диагностики ключа."""
    _ = worst_costs
    return {
        "n_state": diagnostic.n_state,
        "no_ch_min_only": diagnostic.no_ch_min_only,
        "diagnostic": diagnostic,
        "conv_views_to_cart": conv_views_to_cart,
        "conv_views_to_orders": conv_views_to_orders,
        "v2_pay_for_order": resolve_keyword_v2_pay_for_order_cost(calculated_keyword),
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

    all_contexts = await load_campaign_v3_contexts_from_database(
        complex_adv, raw_profiles
    )
    if not all_contexts:
        single = build_keyword_v3_contexts([calculated_keyword], raw_profiles)
        all_contexts = single if single else []
    from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
        V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
        key_orders_per_cart_snapshot,
        load_campaign_orders_per_cart_7d,
        load_rec_orders_per_view_for_v3,
    )

    campaign_orders_per_cart_7d = await load_campaign_orders_per_cart_7d(adv_setting)
    rec_orders_per_view = await load_rec_orders_per_view_for_v3(
        adv_setting,
        rec_system_promotion_mode_active=complex_adv.rec_system_promotion_mode_active,
    )
    ladder_inputs = LadderInputs.from_contexts(
        all_contexts,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        rec_orders_per_view=rec_orders_per_view,
    )
    opc_snapshot = key_orders_per_cart_snapshot(
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        key_orders=calculated_keyword.orders,
        key_carts=calculated_keyword.add_to_cart,
    )

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
    conv_views_to_cart, conv_views_to_orders = _keyword_profile_metrics(
        calculated_keyword
    )

    if (
        diagnostic.n_state
        and not diagnostic.no_ch_min_only
        and not diagnostic.has_ch_position_profile
    ):
        return KeywordV3ProfileData(
            current_mode=calculated_keyword.strategy_mode,
            candidates=_empty_n_state_candidates(),
            **_profile_fields_from_diagnostic(
                calculated_keyword,
                diagnostic,
                conv_views_to_cart=conv_views_to_cart,
                conv_views_to_orders=conv_views_to_orders,
            ),
        )

    eligibility_map = build_eligibility_map(
        all_contexts,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
    )
    ks_id = calculated_keyword.keyword_setting_original_id
    elig = eligibility_map.get(int(ks_id))
    ladder = resolve_ladder_stage_display(ctx, ladder_inputs, eligibility=elig)
    candidates = ladder_view_to_candidates(ladder)
    stage_sources = {
        mode: ladder.stages[mode].source.value for mode in ladder.stages
    }

    from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
        ShelfClickMode,
        resolve_shelf_click_mode_from_adv,
    )

    shelf_click_mode = (
        resolve_shelf_click_mode_from_adv(complex_adv)
        if complex_adv.shelf_promotion_active
        else ShelfClickMode.ORGANIC_DOMINANT
    )
    fields = _profile_fields_from_diagnostic(
        calculated_keyword,
        diagnostic,
        conv_views_to_cart=conv_views_to_cart,
        conv_views_to_orders=conv_views_to_orders,
    )
    return KeywordV3ProfileData(
        current_mode=calculated_keyword.strategy_mode,
        candidates=candidates,
        stage_sources=stage_sources,
        campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        key_orders_7d=opc_snapshot.key_orders_7d,
        key_carts_7d=opc_snapshot.key_carts_7d,
        key_orders_per_cart_raw=opc_snapshot.key_orders_per_cart_raw,
        key_orders_per_cart_smoothed=opc_snapshot.key_orders_per_cart_smoothed,
        prior_carts_strength=opc_snapshot.prior_carts_strength
        or V3_KEY_CART_TO_ORDER_PRIOR_CARTS,
        rec_orders_per_view=rec_orders_per_view,
        shelf_click_mode=shelf_click_mode,
        **fields,
    )


# Публичные aliases для UI list enrich (без импорта private `_…` извне модуля).
load_wb_cabinet = _load_wb_cabinet
build_complex_adv = _build_complex_adv
positions_size_for_adv = _positions_size_for_adv
