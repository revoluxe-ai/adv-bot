"""Загрузка профиля ставок CH для карточки ключа V3 в Telegram."""

from __future__ import annotations

import logging
from typing import cast

from sqlalchemy import select

from app.client_bot.user_interface.views.keyword_v3_profile_ui import KeywordV3ProfileData
from app.core.di.app_container import AppContainer
from app.core.di.di_manager import DIManager
from app.core.di.wb_manager_hub import WBManagerHubFactory
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    build_mode_candidates,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    diagnose_keyword_v3_data,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.profile_utils import (
    profile_points_from_bid_positions,
    resolve_keyword_bid_profile,
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


async def _build_complex_adv(adv_setting: AdvSetting, shop_id: str) -> ComplexAdv:
    """Собрать ``ComplexAdv`` для одной кампании (как в ``get_keywords_for_keyboard``)."""
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


def _profile_load_failure(
    calculated_keyword: CalculatedKeyword,
    *,
    reason: str,
) -> KeywordV3ProfileData:
    """Технический сбой загрузки WB/CH с диагностикой V2/CH по статистике ключа."""
    diagnostic = diagnose_keyword_v3_data(calculated_keyword, None)
    return KeywordV3ProfileData(
        current_mode=calculated_keyword.strategy_mode,
        candidates=_empty_n_state_candidates(),
        n_state=diagnostic.n_state,
        diagnostic=diagnostic,
        load_failure=reason,
    )


async def load_keyword_v3_profile_data(
    adv_setting: AdvSetting,
    calculated_keyword: CalculatedKeyword,
) -> KeywordV3ProfileData | None:
    """Профиль лестницы для одного ключа: CH bid curve + ``build_mode_candidates``.

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
        return _profile_load_failure(calculated_keyword, reason="нет кабинета WB")

    shop_id = wb_cabinet.shop_id
    complex_adv = await _build_complex_adv(adv_setting, shop_id)
    nmids = list(adv_setting.nmids) if adv_setting.nmids else []
    if not nmids:
        return _profile_load_failure(calculated_keyword, reason="нет nmid у кампании")
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
        return _profile_load_failure(
            calculated_keyword, reason="ошибка загрузки min bid WB"
        )

    min_bid = min_bids.search.get(nmid)
    if min_bid is None:
        logger.warning(
            "v3 keyword profile: no min_bid in cache nmid=%s adv_id=%s",
            nmid,
            adv_setting.adv_id,
        )
        return _profile_load_failure(calculated_keyword, reason="min bid не в кеше WB")

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
        return _profile_load_failure(calculated_keyword, reason="ошибка запроса CH")

    bids = resolve_keyword_bid_profile(raw_profiles, calculated_keyword.text)
    profile_points = (
        profile_points_from_bid_positions(bids) if bids else None
    )
    diagnostic = diagnose_keyword_v3_data(calculated_keyword, profile_points)
    if not bids:
        keyword_ctr, conv_views_to_orders = _keyword_profile_metrics(calculated_keyword)
        return KeywordV3ProfileData(
            current_mode=calculated_keyword.strategy_mode,
            candidates=_empty_n_state_candidates(),
            n_state=diagnostic.n_state,
            diagnostic=diagnostic,
            keyword_ctr=keyword_ctr,
            conv_views_to_orders=conv_views_to_orders,
        )

    candidates = build_mode_candidates(
        profile=profile_points,
        keyword_text=calculated_keyword.text,
        conv_views_to_orders=calculated_keyword.conv_views_to_orders,
    )
    keyword_ctr, conv_views_to_orders = _keyword_profile_metrics(calculated_keyword)

    return KeywordV3ProfileData(
        current_mode=calculated_keyword.strategy_mode,
        candidates=candidates,
        n_state=diagnostic.n_state,
        diagnostic=diagnostic,
        keyword_ctr=keyword_ctr,
        conv_views_to_orders=conv_views_to_orders,
    )
