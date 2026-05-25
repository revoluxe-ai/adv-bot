"""Persist AutoUpdater v3 ladder transitions."""

from __future__ import annotations

import logging
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode

from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    step_down,
    step_up,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

_HARD_STATUS_AUTO_MODE = 1
_HARD_STATUS_WHITE_LIST = 2


def _hard_status_allows_up(hard_status: object) -> bool:
    h = int(cast(int, hard_status))
    return h in (_HARD_STATUS_AUTO_MODE, _HARD_STATUS_WHITE_LIST)


def _hard_status_for_strategy_mode(mode: KeywordStrategyMode) -> int:
    """V3: OFF -> авто (1), любой активный режим -> белый список (2)."""
    return (
        _HARD_STATUS_AUTO_MODE
        if mode == KeywordStrategyMode.OFF
        else _HARD_STATUS_WHITE_LIST
    )


async def apply_v3_actions(actions: list[V3Action]) -> None:
    """Apply UP/DOWN/REBALANCE to ``KeywordSetting.strategy_mode`` + ``hard_status``."""
    if not actions:
        return
    async with sm(read_only=False) as session:
        for action in actions:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            if action.action == V3ActionType.REBALANCE_TRANSFER:
                await _apply_transfer(session, action)
                continue
            if action.keyword_setting_id is None:
                continue
            res = await session.execute(
                select(KeywordSetting.strategy_mode, KeywordSetting.hard_status).where(
                    KeywordSetting.id == action.keyword_setting_id
                )
            )
            row = res.one_or_none()
            if row is None:
                logger.warning(
                    "v3 apply skip: KeywordSetting id=%s not found",
                    action.keyword_setting_id,
                )
                continue
            current, hard_status = row
            if action.action == V3ActionType.UP:
                if not _hard_status_allows_up(hard_status):
                    logger.debug(
                        "v3 apply skip UP: hard_status_mismatch_up id=%s hard_status=%s",
                        action.keyword_setting_id,
                        hard_status,
                    )
                    continue
                nxt = step_up(current)
                if nxt is None:
                    continue
                if current == KeywordStrategyMode.OFF and nxt != KeywordStrategyMode.MIN_CPA:
                    continue
                hs = _hard_status_for_strategy_mode(nxt)
                _ = await session.execute(
                    update(KeywordSetting)
                    .where(KeywordSetting.id == action.keyword_setting_id)
                    .values(strategy_mode=nxt, hard_status=hs)
                )
            elif action.action == V3ActionType.DOWN:
                if int(cast(int, hard_status)) != _HARD_STATUS_WHITE_LIST:
                    logger.debug(
                        "v3 apply skip DOWN: hard_status_mismatch_down id=%s hard_status=%s",
                        action.keyword_setting_id,
                        hard_status,
                    )
                    continue
                nxt = step_down(current)
                if nxt is None:
                    continue
                hs = _hard_status_for_strategy_mode(nxt)
                _ = await session.execute(
                    update(KeywordSetting)
                    .where(KeywordSetting.id == action.keyword_setting_id)
                    .values(strategy_mode=nxt, hard_status=hs)
                )
        await session.commit()


async def _apply_transfer(session: AsyncSession, action: V3Action) -> None:
    if action.from_keyword_setting_id is None or action.to_keyword_setting_id is None:
        return
    res_from = await session.execute(
        select(KeywordSetting.strategy_mode, KeywordSetting.hard_status).where(
            KeywordSetting.id == action.from_keyword_setting_id
        )
    )
    res_to = await session.execute(
        select(KeywordSetting.strategy_mode, KeywordSetting.hard_status).where(
            KeywordSetting.id == action.to_keyword_setting_id
        )
    )
    row_from = res_from.one_or_none()
    row_to = res_to.one_or_none()
    if row_from is None or row_to is None:
        return
    mode_from, hard_status_from = row_from
    mode_to, hard_status_to = row_to
    if int(cast(int, hard_status_from)) != _HARD_STATUS_WHITE_LIST:
        logger.debug(
            "v3 transfer skip: hard_status_mismatch_down id=%s hard_status=%s",
            action.from_keyword_setting_id,
            hard_status_from,
        )
        return
    if not _hard_status_allows_up(hard_status_to):
        logger.debug(
            "v3 transfer skip: hard_status_mismatch_up id=%s hard_status=%s",
            action.to_keyword_setting_id,
            hard_status_to,
        )
        return
    if mode_from == KeywordStrategyMode.OFF:
        return
    down = step_down(mode_from)
    up = step_up(mode_to)
    if down is None or up is None:
        return
    if mode_to != KeywordStrategyMode.OFF:
        return
    if up != KeywordStrategyMode.MIN_CPA:
        return
    _ = await session.execute(
        update(KeywordSetting)
        .where(KeywordSetting.id == action.from_keyword_setting_id)
        .values(
            strategy_mode=down,
            hard_status=_hard_status_for_strategy_mode(down),
        )
    )
    _ = await session.execute(
        update(KeywordSetting)
        .where(KeywordSetting.id == action.to_keyword_setting_id)
        .values(
            strategy_mode=up,
            hard_status=_hard_status_for_strategy_mode(up),
        )
    )
