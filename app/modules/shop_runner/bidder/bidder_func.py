"""Legacy bidder with an optional V3 safety cap preloaded per campaign."""

import logging
from dataclasses import dataclass

from dependency_injector.wiring import inject, Provide
import typing
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.old_modules.adv_common_parameters_manager.adv_parameter_manager import (
    AdvParameterManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.candidates import (
    aggression_target_for_stored_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.loaders import (
    load_v3_wb_context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
    build_keyword_v3_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
    state_candidates_by_mode_for_ctx,
)
from app.modules.shop_runner.service_manager.services.v3_point_order_cpo import (
    load_campaign_orders_per_cart_7d,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import (
    ComplexAdv,
    WBShopDataManager,
)

from app.settings import settings

from app.utils.db.session_maker import get_async_session_maker as sm
from .redis_cache.last_keyword_stamp_timestamp_cache import (
    LastKeywordStampTimestampCache,
)

from ...wb_adv_updater import data_manager
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

if typing.TYPE_CHECKING:
    from app.modules.shop_runner.bidder.redis_cache.redis_last_total_views import (
        RedisLastTotalViews,
    )



from ..modules.wb_api import WBApi

logger = logging.getLogger(__name__)

# TODO: включить проверку РК: обновлять только если РК активна и не приостановлена


@dataclass(frozen=True, slots=True)
class BidderV3SafetyCapContext:
    """Preloaded V3 row for bidder safety-cap checks.

    The map is keyed by ``keyword_setting_original_id`` and built once per
    campaign before the bidder loop. The bidder consumes it without any extra
    V3/profile queries.
    """

    keyword_setting_original_id: int
    current_mode: KeywordStrategyMode | None
    current_target_place: int | None
    matrix_state_bid: int | None
    fact_pay_for_order: float | None
    max_pay_for_order: float | None
    overspend: bool
    skip_reason: str | None = None


async def get_cpms_from_wb(advs: list[AuctionAdv]) -> set[int] | None:
    cpms = {adv.cpm for adv in advs if adv.cpm is not None}
    return cpms if cpms else None


async def _update_and_get_advs_from_wb(
    auto_adv: AdvSetting, wb_api: WBApi
) -> list[AuctionAdv]:
    adv_ids: set[int] = set()
    if auto_adv.bidder_for_auto:
        adv_ids.add(auto_adv.adv_id)
    if search_adv_id := auto_adv.search_adv_id:
        adv_ids.add(search_adv_id)
    if not adv_ids:
        return []
    advs: list[AuctionAdv] = await wb_api.get_advs(list(adv_ids))
    try:
        assert wb_api.access.wb_cabinet is not None
        wb_cabinet_original_id: int = int(wb_api.access.wb_cabinet.id)
        await wb_db_manager.update_advs_in_db(advs, wb_cabinet_original_id)
    except Exception:  # noqa
        logger.error("Ошибка обновления РК в базе", exc_info=True)
    return advs



async def __get_new_cpm_by_position(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    best_keyword: CalculatedKeyword,
    cpm_now: int,
    technical_min_cpm: int,
) -> int | None:
    adv_id = adv_setting.adv_id
    shop_id = wb_api.shop_id

    max_cpm = adv_setting.max_cpm
    if max_cpm is None:
        return None
    step = adv_setting.bidder_step or settings.BIDDER_STEP
    max_position = adv_setting.max_place
    if max_position is None:
        return None
    promo_position: float = best_keyword.position
    if 0 < promo_position <= max_position:
        new_cpm: int = cpm_now - step
    else:
        new_cpm = cpm_now + step
    new_cpm = max(min(new_cpm, max_cpm), technical_min_cpm)

    if new_cpm == max_cpm and adv_setting.reset_place:
        async with sm(read_only=False) as session:
            assert adv_setting
            adv_setting_for_update: AdvSetting | None = await session.get(
                AdvSetting, adv_setting.id
            )
            if adv_setting_for_update is None:
                logger.error(f"[{shop_id}] [{adv_id}] Настройки РК не найдены")
                raise Exception("Настройки РК не найдены")
            adv_setting_for_update.max_place = int(promo_position + 1 + 0.5)
            await session.commit()

    logger.debug(f"[{shop_id}] [{adv_id}] Ставки обновлены")
    return new_cpm


def _rounded_matrix_state_bid(candidate: object | None) -> int | None:
    """Вернуть bid из V3 matrix в формате bidder/UI (целое CPM)."""
    if candidate is None:
        return None
    bid = getattr(candidate, "bid", None)
    if bid is None or not getattr(candidate, "is_valid", False):
        return None
    rounded = int(float(bid) + 0.5)
    return rounded if rounded > 0 else None


async def build_v3_safety_cap_by_keyword_setting_original_id(
    complex_adv: ComplexAdv,
    keywords: list[CalculatedKeyword],
    *,
    wb_shop_data_manager: WBShopDataManager,
) -> dict[int, BidderV3SafetyCapContext]:
    """Preload V3 safety-cap rows for all bidder-managed keywords in one pass.

    The helper mirrors the production UI/profile source of truth:
    ``BidPosition -> PositionProfilePoint -> build_mode_candidates ->
    ModeCandidate.bid``.
    """
    try:
        dto, raw_profiles = await load_v3_wb_context(
            complex_adv,
            wb_shop_data_manager=wb_shop_data_manager,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "[adv_id=%s] V3 safety cap preload failed; fallback to legacy bidder",
            complex_adv.adv_id,
            exc_info=True,
        )
        return {}
    if dto is None or not raw_profiles:
        return {}

    try:
        campaign_orders_per_cart_7d = await load_campaign_orders_per_cart_7d(
            complex_adv.adv_setting
        )
        all_contexts = build_keyword_v3_contexts(keywords, raw_profiles)
        ladder_inputs = LadderInputs.from_contexts(
            all_contexts,
            campaign_orders_per_cart_7d=campaign_orders_per_cart_7d,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "[adv_id=%s] V3 safety cap context build failed; fallback to legacy bidder",
            complex_adv.adv_id,
            exc_info=True,
        )
        return {}

    fact_pay_for_order = dto.fact_pay_for_order
    max_pay_for_order = dto.plan.max_pay_for_order
    overspend = (
        fact_pay_for_order is not None and fact_pay_for_order > max_pay_for_order
    )
    if not overspend:
        return {}

    result: dict[int, BidderV3SafetyCapContext] = {}
    for ctx in all_contexts:
        keyword_setting_original_id = int(ctx.keyword.keyword_setting_original_id or 0)
        if keyword_setting_original_id <= 0:
            continue
        current_mode = ctx.keyword.strategy_mode
        if current_mode == KeywordStrategyMode.OFF:
            continue
        agg_mode = aggression_target_for_stored_mode(current_mode)
        if agg_mode is None:
            continue
        candidates = state_candidates_by_mode_for_ctx(ctx, ladder_inputs)
        matrix_state_bid = _rounded_matrix_state_bid(candidates.get(agg_mode))
        if matrix_state_bid is None:
            continue
        result[keyword_setting_original_id] = BidderV3SafetyCapContext(
            keyword_setting_original_id=keyword_setting_original_id,
            current_mode=current_mode,
            current_target_place=ctx.keyword.target_place,
            matrix_state_bid=matrix_state_bid,
            fact_pay_for_order=fact_pay_for_order,
            max_pay_for_order=max_pay_for_order,
            overspend=overspend,
        )
    return result


def _apply_v3_safety_cap(
    *,
    new_cpm: int,
    technical_min_cpm: int,
    cap_context: BidderV3SafetyCapContext | None,
) -> tuple[int | None, str | None]:
    """Clamp bidder CPM to V3 cap or skip when cap is technically impossible."""
    if cap_context is None or not cap_context.overspend:
        return new_cpm, None
    cap = cap_context.matrix_state_bid
    if cap is None or cap <= 0:
        return new_cpm, None
    if cap < technical_min_cpm:
        return None, "v3_safety_cap_below_technical_min"
    if new_cpm > cap:
        return cap, None
    return new_cpm, None


@inject
async def run_bidder_process_for_adv(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    keywords: list[CalculatedKeyword],
    v3_safety_cap_by_keyword_setting_original_id: dict[
        int, BidderV3SafetyCapContext
    ] | None = None,
    redis_last_total_views: "RedisLastTotalViews" = Provide[
        "module_resources.bidder_container.redis_last_total_views"
    ],
    last_keyword_stamp_timestamp_cache: LastKeywordStampTimestampCache = Provide[
        "module_resources.bidder_container.last_keyword_stamp_timestamp_cache"
    ],
) -> None:
    """Legacy bidder: пишет CPM для Авто и/или Search по флагам AdvSetting.

    При ``auto_shelf_bid_control_enabled`` (UI «Управление ставкой в полках»)
    путь ``bidder_for_auto`` MUST NOT писать ставку Авто — ownership у
    AutoShelfBidControlManager (spec auto-bid-module-coexistence / Mutual exclusion).
    Search ``update_cpm(search_adv_id)`` этим gate не блокируется.
    """
    advs: list[AuctionAdv] = await _update_and_get_advs_from_wb(adv_setting, wb_api)
    advs_from_wb_with_active_company: list[AuctionAdv] = [
        adv for adv in advs if adv.status_native == "started"
    ]

    cpms: set[int] | None = await get_cpms_from_wb(advs_from_wb_with_active_company)
    cpm_now = max(cpms) if cpms else None
    if not cpm_now:
        logger.debug(
            "Не удалось определить текущую ставку для shop_id: %s, adv_id: %s",
            wb_api.shop_id,
            adv_setting.adv_id,
        )
        return None

    user_max_cpm = adv_setting.max_cpm
    if not user_max_cpm:
        return None
    technical_min_cpm = await AdvParameterManager().get_min_cpm(adv_setting)
    white_list = [kw for kw in keywords if kw.hard_status in (2, 4)]
    best_keyword = data_manager.get_best_keyword(white_list)
    if not best_keyword:
        return None
    # TODO: Надо тут перепроверить логику выбора режима, включая что по умолчанию в модели и т.д.

    last_views = await redis_last_total_views.get(best_keyword)
    if last_views and last_views > 0 and last_views == best_keyword.total_views:
        return None

    last_time_stamp = await last_keyword_stamp_timestamp_cache.get(best_keyword)
    if last_time_stamp and last_time_stamp == best_keyword.timestamp:
        return None
    new_cpm = await __get_new_cpm_by_position(
        adv_setting,
        wb_api,
        best_keyword,
        cpm_now,
        technical_min_cpm,
    )
    if not new_cpm:
        return None

    cap_context = None
    if v3_safety_cap_by_keyword_setting_original_id:
        cap_context = v3_safety_cap_by_keyword_setting_original_id.get(
            int(best_keyword.keyword_setting_original_id)
        )
    new_cpm, skip_reason = _apply_v3_safety_cap(
        new_cpm=new_cpm,
        technical_min_cpm=technical_min_cpm,
        cap_context=cap_context,
    )
    if skip_reason is not None:
        logger.warning(
            "[%s] [%s] Skip CPM update: %s",
            wb_api.shop_id,
            adv_setting.adv_id,
            skip_reason,
        )
        return None
    if new_cpm is None:
        return None

    if not adv_setting.nmids:
        raise RuntimeError("Пустой список nmids - это недопустимое состояние")

    nmid = adv_setting.nmids[0]

    if new_cpm != cpm_now:
        # Mutual exclusion (auto-bid-module-coexistence): shelves ON → ignore legacy Auto write.
        shelf_bid_control_on = bool(
            getattr(adv_setting, "auto_shelf_bid_control_enabled", False)
        )
        if adv_setting.bidder_for_auto and not shelf_bid_control_on:
            auto_adv_id = int(adv_setting.adv_id)
            assert auto_adv_id is not None
            await wb_api.update_cpm(
                auto_adv_id,
                nmid,
                new_cpm,
            )

        if adv_setting.search_adv_id:
            await wb_api.update_cpm(
                adv_setting.search_adv_id,
                nmid,
                new_cpm,
            )
        await redis_last_total_views.set(best_keyword)
        await last_keyword_stamp_timestamp_cache.set(best_keyword)
    return None
