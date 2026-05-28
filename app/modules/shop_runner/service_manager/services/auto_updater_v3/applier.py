"""Persist AutoUpdater v3 ladder transitions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
    step_down,
    step_up,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.last_action_redis import (
    LastV3UpdaterActionRedisCache,
    build_snapshot_from_applied,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2

# Порядок применения в одном цикле: сначала выключаем/понижаем, затем поднимаем,
# чтобы UP не опирался на устаревший strategy_mode до DOWN/FORCE_OFF того же тика.
V3_ACTION_APPLY_ORDER: dict[V3ActionType, int] = {
    V3ActionType.FORCE_OFF: 0,
    V3ActionType.DOWN: 1,
    V3ActionType.UP: 2,
    V3ActionType.REBALANCE_TRANSFER: 3,
    V3ActionType.DO_NOTHING: 4,
}


@dataclass(frozen=True)
class AppliedV3Action:
    """Факт успешного изменения ``strategy_mode`` за цикл V3."""

    action: V3ActionType
    keyword_setting_id: int | None
    keyword_text: str
    from_mode: KeywordStrategyMode
    to_mode: KeywordStrategyMode
    reason: str


def hard_status_allows_up(hard_status: object) -> bool:
    h = int(cast(int, hard_status))
    return h in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def hard_status_allows_force_off(hard_status: object) -> bool:
    """FORCE_OFF: БС; не трогаем turn_off (3) и always_on (4)."""
    h = int(cast(int, hard_status))
    return h in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def hard_status_for_strategy_mode(mode: KeywordStrategyMode) -> int:
    """V3: OFF -> авто (1), любой активный режим -> белый список (2)."""
    return (
        _HARD_STATUS_AUTO_MODE
        if mode == KeywordStrategyMode.OFF
        else _HARD_STATUS_WHITE_LIST
    )


def resolve_v3_action_target_mode(
    action: V3Action,
    current: KeywordStrategyMode,
) -> KeywordStrategyMode | None:
    """Целевой режим для UP/DOWN или None, если действие неприменимо."""
    if action.action == V3ActionType.UP:
        if action.target_strategy_mode is not None:
            nxt = action.target_strategy_mode
            if mode_level(nxt) <= mode_level(current):
                return None
            return nxt
        return step_up(current)
    if action.action == V3ActionType.DOWN:
        if action.target_strategy_mode is not None:
            nxt = action.target_strategy_mode
            if mode_level(nxt) >= mode_level(current):
                return None
            return nxt
        return step_down(current)
    return None


def can_persist_netto_mode_change(
    db_current: KeywordStrategyMode,
    desired: KeywordStrategyMode,
    hard_status: object,
) -> bool:
    """Можно ли записать нетто-режим при свежем ``hard_status`` из БД."""
    if db_current == desired:
        return False
    h = int(cast(int, hard_status))
    if h not in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST):
        return False
    if mode_level(desired) < mode_level(db_current):
        if desired == KeywordStrategyMode.OFF:
            return db_current != KeywordStrategyMode.OFF
        return h == _HARD_STATUS_WHITE_LIST
    if mode_level(desired) > mode_level(db_current):
        return True
    return False


async def _keyword_text_by_id(
    session: AsyncSession,
    cache: dict[int, str],
    keyword_setting_id: int,
) -> str:
    if keyword_setting_id in cache:
        return cache[keyword_setting_id]
    res = await session.execute(
        select(KeywordSetting.text).where(KeywordSetting.id == keyword_setting_id)
    )
    text = res.scalar_one_or_none() or ""
    cache[keyword_setting_id] = text
    return text


async def persist_last_applied_v3(
    adv: AdvSetting,
    applied: list[AppliedV3Action],
) -> None:
    if not applied:
        return
    last = applied[-1]
    up_count = sum(1 for a in applied if a.action == V3ActionType.UP)
    down_count = sum(1 for a in applied if a.action == V3ActionType.DOWN)
    off_count = sum(1 for a in applied if a.action == V3ActionType.FORCE_OFF)
    mechanism: dict[str, int] = {"m1": 0, "m2": 0, "m3": 0, "other": 0}
    for item in applied:
        if item.reason.startswith("m1_"):
            mechanism["m1"] += 1
        elif item.reason.startswith("m2_"):
            mechanism["m2"] += 1
        elif item.reason.startswith("m3_"):
            mechanism["m3"] += 1
        else:
            mechanism["other"] += 1
    snapshot = build_snapshot_from_applied(
        action=last.action,
        keyword_text=last.keyword_text,
        keyword_setting_id=last.keyword_setting_id,
        from_mode=last.from_mode,
        to_mode=last.to_mode,
        reason=last.reason,
        batch_extra_count=0,
        cycle_aggregate={
            "up": up_count,
            "down": down_count,
            "force_off": off_count,
            "mechanism": mechanism,
        },
    )
    await LastV3UpdaterActionRedisCache(adv).set(snapshot)


async def apply_v3_actions(
    actions: list[V3Action],
    *,
    complex_adv: ComplexAdv,
) -> None:
    """Немедленно применить UP/DOWN/FORCE_OFF/REBALANCE (legacy / unit tests).

    Оркестратор V3 использует ``V3TickKeywordLedger`` + ``flush_to_db`` в конце тика.
    """
    if not actions:
        return
    applied: list[AppliedV3Action] = []
    ordered_actions = sorted(
        actions, key=lambda a: V3_ACTION_APPLY_ORDER.get(a.action, 99)
    )
    async with sm(read_only=False) as session:
        text_cache: dict[int, str] = {}
        for action in ordered_actions:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            if action.action == V3ActionType.REBALANCE_TRANSFER:
                transfer_applied = await _apply_transfer(session, action, text_cache)
                applied.extend(transfer_applied)
                continue
            if action.keyword_setting_id is None:
                continue
            ks_id = action.keyword_setting_id
            res = await session.execute(
                select(KeywordSetting.strategy_mode, KeywordSetting.hard_status).where(
                    KeywordSetting.id == ks_id
                )
            )
            row = res.one_or_none()
            if row is None:
                logger.warning(
                    "v3 apply skip: KeywordSetting id=%s not found",
                    ks_id,
                )
                continue
            current, hard_status = row
            if action.action == V3ActionType.UP:
                if not hard_status_allows_up(hard_status):
                    logger.debug(
                        "v3 apply skip UP: hard_status_mismatch_up id=%s hard_status=%s",
                        ks_id,
                        hard_status,
                    )
                    continue
                nxt = resolve_v3_action_target_mode(action, current)
                if nxt is None:
                    continue
                hs = hard_status_for_strategy_mode(nxt)
                _ = await session.execute(
                    update(KeywordSetting)
                    .where(KeywordSetting.id == ks_id)
                    .values(strategy_mode=nxt, hard_status=hs)
                )
                kw_text = await _keyword_text_by_id(session, text_cache, ks_id)
                applied.append(
                    AppliedV3Action(
                        action=V3ActionType.UP,
                        keyword_setting_id=ks_id,
                        keyword_text=kw_text,
                        from_mode=current,
                        to_mode=nxt,
                        reason=action.reason,
                    )
                )
            elif action.action == V3ActionType.DOWN:
                if int(cast(int, hard_status)) != _HARD_STATUS_WHITE_LIST:
                    logger.debug(
                        "v3 apply skip DOWN: hard_status_mismatch_down id=%s hard_status=%s",
                        ks_id,
                        hard_status,
                    )
                    continue
                nxt = resolve_v3_action_target_mode(action, current)
                if nxt is None:
                    continue
                hs = hard_status_for_strategy_mode(nxt)
                _ = await session.execute(
                    update(KeywordSetting)
                    .where(KeywordSetting.id == ks_id)
                    .values(strategy_mode=nxt, hard_status=hs)
                )
                kw_text = await _keyword_text_by_id(session, text_cache, ks_id)
                applied.append(
                    AppliedV3Action(
                        action=V3ActionType.DOWN,
                        keyword_setting_id=ks_id,
                        keyword_text=kw_text,
                        from_mode=current,
                        to_mode=nxt,
                        reason=action.reason,
                    )
                )
            elif action.action == V3ActionType.FORCE_OFF:
                if current == KeywordStrategyMode.OFF:
                    continue
                if not hard_status_allows_force_off(hard_status):
                    logger.debug(
                        "v3 apply skip FORCE_OFF: hard_status_mismatch id=%s hard_status=%s",
                        ks_id,
                        hard_status,
                    )
                    continue
                hs = hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
                _ = await session.execute(
                    update(KeywordSetting)
                    .where(KeywordSetting.id == ks_id)
                    .values(
                        strategy_mode=KeywordStrategyMode.OFF,
                        hard_status=hs,
                    )
                )
                kw_text = await _keyword_text_by_id(session, text_cache, ks_id)
                applied.append(
                    AppliedV3Action(
                        action=V3ActionType.FORCE_OFF,
                        keyword_setting_id=ks_id,
                        keyword_text=kw_text,
                        from_mode=current,
                        to_mode=KeywordStrategyMode.OFF,
                        reason=action.reason,
                    )
                )
        await session.commit()

    adv = getattr(complex_adv, "adv_setting", None)
    if adv is not None and applied:
        await persist_last_applied_v3(adv, applied)


async def _apply_transfer(
    session: AsyncSession,
    action: V3Action,
    text_cache: dict[int, str],
) -> list[AppliedV3Action]:
    """REBALANCE: down source + up target; snapshot — по целевому ключу (up)."""
    if action.from_keyword_setting_id is None or action.to_keyword_setting_id is None:
        return []
    from_id = action.from_keyword_setting_id
    to_id = action.to_keyword_setting_id
    res_from = await session.execute(
        select(KeywordSetting.strategy_mode, KeywordSetting.hard_status).where(
            KeywordSetting.id == from_id
        )
    )
    res_to = await session.execute(
        select(KeywordSetting.strategy_mode, KeywordSetting.hard_status).where(
            KeywordSetting.id == to_id
        )
    )
    row_from = res_from.one_or_none()
    row_to = res_to.one_or_none()
    if row_from is None or row_to is None:
        return []
    mode_from, hard_status_from = row_from
    mode_to, hard_status_to = row_to
    if int(cast(int, hard_status_from)) != _HARD_STATUS_WHITE_LIST:
        logger.debug(
            "v3 transfer skip: hard_status_mismatch_down id=%s hard_status=%s",
            from_id,
            hard_status_from,
        )
        return []
    if not hard_status_allows_up(hard_status_to):
        logger.debug(
            "v3 transfer skip: hard_status_mismatch_up id=%s hard_status=%s",
            to_id,
            hard_status_to,
        )
        return []
    if mode_from == KeywordStrategyMode.OFF:
        return []
    down = step_down(mode_from)
    up = step_up(mode_to)
    if down is None or up is None:
        return []
    if mode_to != KeywordStrategyMode.OFF:
        return []
    if up != KeywordStrategyMode.MIN_CPA:
        return []
    _ = await session.execute(
        update(KeywordSetting)
        .where(KeywordSetting.id == from_id)
        .values(
            strategy_mode=down,
            hard_status=hard_status_for_strategy_mode(down),
        )
    )
    _ = await session.execute(
        update(KeywordSetting)
        .where(KeywordSetting.id == to_id)
        .values(
            strategy_mode=up,
            hard_status=hard_status_for_strategy_mode(up),
        )
    )
    to_text = await _keyword_text_by_id(session, text_cache, to_id)
    return [
        AppliedV3Action(
            action=V3ActionType.REBALANCE_TRANSFER,
            keyword_setting_id=to_id,
            keyword_text=to_text,
            from_mode=mode_to,
            to_mode=up,
            reason=action.reason,
        )
    ]
