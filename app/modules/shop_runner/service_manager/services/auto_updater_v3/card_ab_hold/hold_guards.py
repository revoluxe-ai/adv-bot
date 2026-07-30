"""HOLD overspend/PFO guards без ordinary NORMAL preamble.

Spec ``card-ab-hold-mode``: при ACTIVE только guard перерасхода vs max CPO;
без TP update / WL / enable / calibration UP.

Owner A_PRIME / PBH-002: symmetric ``pfo_recovery`` / ``return_on`` /
``restore_on`` when a confirmed-set keyword recovers (PASS) after safety OFF.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    hard_status_for_strategy_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
    cmp_over_threshold,
    pfo_off_plan_headroom_floor,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    keyword_pfo_over_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    is_v3_operable_hard_status,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

# auto_on floor after pfo_recovery (same as setup return_on).
_AB_HOLD_RECOVERY_ON_MODE = KeywordStrategyMode.MIN_CPA


def is_ab_hold_campaign_deep_overspend(
    *,
    fact_pay_for_order: float | None,
    max_pay_for_order: float,
) -> bool:
    """True, если fact в зоне pfo_off (как ``is_deep_overspend`` без AdvState)."""
    if fact_pay_for_order is None:
        return False
    max_pay = float(max_pay_for_order)
    if max_pay <= 0:
        return False
    return cmp_over_threshold(
        float(fact_pay_for_order),
        pfo_off_plan_headroom_floor(max_pay),
    )


def select_ab_hold_overspend_off_keyword_ids(
    keywords: list[CalculatedKeyword],
    *,
    max_pay_for_order: float,
) -> list[int]:
    """Operable active ключи с pay_for_order > max (HOLD PFO-off guard)."""
    ceiling = float(max_pay_for_order)
    out: list[int] = []
    for kw in keywords:
        if not is_v3_operable_hard_status(kw.hard_status):
            continue
        if kw.strategy_mode == KeywordStrategyMode.OFF:
            continue
        if not keyword_pfo_over_max(kw.pay_for_order, ceiling):
            continue
        out.append(int(kw.keyword_setting_original_id))
    return out


def select_ab_hold_pfo_recovery_on_keyword_ids(
    keywords: list[CalculatedKeyword],
    *,
    max_pay_for_order: float,
    allowed_phrases: Iterable[str] | None = None,
) -> list[int]:
    """Ids for return_on / restore_on after PFO recovers within confirmed set.

    Owner A_PRIME: SAFETY_OFF when PFO>max Allowed; AUTO_ON when PFO recovers
    within frozen confirmed set. Does not change membership.

    Args:
        keywords: calculated keywords for the campaign.
        max_pay_for_order: plan max CPO ceiling.
        allowed_phrases: confirmed-set texts; ``None`` = no membership filter.

    Returns:
        keyword_setting ids currently OFF that classify PASS (pfo_recovery).
    """
    ceiling = float(max_pay_for_order)
    allowed: set[str] | None = (
        {str(t) for t in allowed_phrases} if allowed_phrases is not None else None
    )
    on_ids: list[int] = []
    for kw in keywords:
        if not is_v3_operable_hard_status(kw.hard_status):
            continue
        try:
            if int(kw.strategy_mode) != int(KeywordStrategyMode.OFF):
                continue
        except (TypeError, ValueError):
            if kw.strategy_mode is not KeywordStrategyMode.OFF:
                continue
        text = str(getattr(kw, "text", None) or "")
        if allowed is not None and text not in allowed:
            continue
        action = classify_ab_hold_setup_keyword(
            pay_for_order=kw.pay_for_order,
            views=int(kw.views),
            max_pay_for_order=ceiling,
        )
        if action != AbHoldSetupAction.PASS_FIX_TARGET:
            continue
        on_ids.append(int(kw.keyword_setting_original_id))
    return on_ids


async def apply_ab_hold_overspend_offs_in_session(
    session: AsyncSession,
    *,
    keyword_ids: list[int],
) -> int:
    """Persist FORCE_OFF в переданной PG session (hold-guard overspend).

    Parent orchestration открывает WRITE session maker и передаёт session
    сюда — injectable seam для live PG integration evidence.

    Args:
        session: injectable async session (WRITE / commit).
        keyword_ids: keyword_setting ids to FORCE_OFF.

    Returns:
        Число обновлённых id (0 если список пуст).
    """
    if not keyword_ids:
        return 0
    off_hs = hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
    stmt = (
        update(KeywordSetting)
        .where(KeywordSetting.id.in_(keyword_ids))
        .values(
            hard_status=off_hs,
            strategy_mode=KeywordStrategyMode.OFF,
            target_place=None,
        )
    )
    _ = await session.execute(stmt)
    await session.commit()
    return len(keyword_ids)


async def apply_ab_hold_overspend_offs(
    *,
    adv_id: int,
    keyword_ids: list[int],
) -> int:
    """Persist FORCE_OFF для hold-guard (strategy_mode OFF + hard_status).

    Parent WRITE seam: ``sm(read_only=False)`` →
    ``apply_ab_hold_overspend_offs_in_session``.

    Returns:
        Число обновлённых id.
    """
    if not keyword_ids:
        return 0
    async with sm(read_only=False) as session:
        updated = await apply_ab_hold_overspend_offs_in_session(
            session,
            keyword_ids=keyword_ids,
        )
    logger.info(
        "[adv_id=%s] ab_hold overspend OFF count=%s",
        adv_id,
        updated,
    )
    return updated


def _normalize_confirmed_target_places(
    confirmed_target_places: Mapping[int | str, int] | None,
    keyword_ids: list[int],
) -> dict[int, int]:
    """Собрать id→TP из SoT-карты для recovery_on (PBH-009).

    Ключи карты — ``KeywordSetting.id`` (int или str). Ids вне
    ``keyword_ids`` игнорируются; отсутствующий TP для id означает, что
    колонка ``target_place`` в этом UPDATE не пишется.

    Args:
        confirmed_target_places: epoch confirmed JSON SoT (id→TP) или None.
        keyword_ids: ids, для которых выполняется return_on.

    Returns:
        Подмножество id→int(target_place) только для восстанавливаемых ids.
    """
    if not confirmed_target_places:
        return {}
    out: dict[int, int] = {}
    for raw_id in keyword_ids:
        ks_id = int(raw_id)
        place = confirmed_target_places.get(ks_id)
        if place is None:
            place = confirmed_target_places.get(str(ks_id))
        if place is None:
            continue
        out[ks_id] = int(place)
    return out


async def apply_ab_hold_pfo_recovery_ons_in_session(
    session: AsyncSession,
    *,
    keyword_ids: list[int],
    confirmed_target_places: Mapping[int | str, int] | None = None,
) -> int:
    """Persist return_on / recovery_on в переданной PG session (A_PRIME auto_on).

    Parent orchestration открывает WRITE session maker и передаёт session
    сюда — injectable seam для live PG integration evidence.

    PBH-009: после overspend OFF (``target_place=None``) recovery MUST
    восстановить confirmed ``target_place`` из epoch SoT-карты, иначе bidder
    уходит в ``snap_to_min``.

    Args:
        session: injectable async session (WRITE / commit).
        keyword_ids: keyword_setting ids to restore_on (MIN_CPA).
        confirmed_target_places: id→confirmed TP из
            ``card_ab_hold_confirmed_target_places_json`` (после резолва
            text→id на call site). ``None``/пусто — TP не трогаем.

    Returns:
        Число обновлённых id (0 если список пуст).
    """
    if not keyword_ids:
        return 0
    on_hs = hard_status_for_strategy_mode(_AB_HOLD_RECOVERY_ON_MODE)
    id_to_place = _normalize_confirmed_target_places(
        confirmed_target_places, keyword_ids
    )
    # Group by restored TP (None = leave column untouched) for O(distinct places)
    # round-trips; literals keep Update._values inspectable (unit contract).
    by_place: dict[int | None, list[int]] = {}
    for ks_id in keyword_ids:
        place = id_to_place.get(int(ks_id))
        by_place.setdefault(place, []).append(int(ks_id))
    for place, ids in by_place.items():
        values: dict[str, object] = {
            "hard_status": on_hs,
            "strategy_mode": _AB_HOLD_RECOVERY_ON_MODE,
        }
        if place is not None:
            values["target_place"] = place
        stmt_return_on = (
            update(KeywordSetting)
            .where(KeywordSetting.id.in_(ids))
            .values(**values)
        )
        _ = await session.execute(stmt_return_on)
    await session.commit()
    return len(keyword_ids)


async def apply_ab_hold_pfo_recovery_ons(
    *,
    adv_id: int,
    keyword_ids: list[int],
    confirmed_target_places: Mapping[int | str, int] | None = None,
) -> int:
    """Persist return_on / recovery_on after PFO recovers (A_PRIME auto_on).

    Parent WRITE seam: ``sm(read_only=False)`` →
    ``apply_ab_hold_pfo_recovery_ons_in_session``.

    Args:
        adv_id: campaign id (logging).
        keyword_ids: keyword_setting ids to restore_on (MIN_CPA).
        confirmed_target_places: id→confirmed TP SoT (PBH-009); optional.

    Returns:
        Число обновлённых id.
    """
    if not keyword_ids:
        return 0
    async with sm(read_only=False) as session:
        updated = await apply_ab_hold_pfo_recovery_ons_in_session(
            session,
            keyword_ids=keyword_ids,
            confirmed_target_places=confirmed_target_places,
        )
    logger.info(
        "[adv_id=%s] ab_hold pfo_recovery return_on count=%s",
        adv_id,
        updated,
    )
    return updated
