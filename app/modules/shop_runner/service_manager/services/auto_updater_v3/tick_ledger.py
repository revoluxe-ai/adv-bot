"""In-memory ladder state за один тик V3 и нетто-flush в БД.

Фазы (M1, trim, no_data, selector) планируют действия и мутируют ``CalculatedKeyword``
in-memory; в конце тика — один commit только ``strategy_mode`` + ``hard_status`` для
ключей, у которых нетто-режим отличается от baseline, с bulk-проверкой свежего
``hard_status`` в БД (отбрасываем ``hard_status`` не in {1, 2}).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    AppliedV3Action,
    V3_ACTION_APPLY_ORDER,
    can_persist_netto_mode_change,
    hard_status_for_strategy_mode,
    hard_status_allows_force_off,
    hard_status_allows_up,
    persist_last_applied_v3,
    resolve_v3_action_target_mode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.ladder import (
    mode_level,
    step_down,
    step_up,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

_HARD_STATUS_WHITE_LIST = 2


@dataclass
class V3TickKeywordLedger:
    """Снимок ключей на тик: baseline + in-memory нетто-режимы."""

    keywords: list[CalculatedKeyword]
    _by_id: dict[int, CalculatedKeyword] = field(default_factory=dict)
    _baseline_mode: dict[int, KeywordStrategyMode] = field(default_factory=dict)
    _last_reason: dict[int, str] = field(default_factory=dict)
    _netto_action_type: dict[int, V3ActionType] = field(default_factory=dict)
    _tick_applied: list[AppliedV3Action] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._reindex()

    def _reindex(self) -> None:
        self._by_id = {}
        for kw in self.keywords:
            ks_id = kw.keyword_setting_original_id
            if ks_id is not None:
                self._by_id[int(ks_id)] = kw

    @classmethod
    def from_keywords(cls, keywords: list[CalculatedKeyword]) -> V3TickKeywordLedger:
        """Создать ledger и зафиксировать baseline ``strategy_mode`` по каждому ключу."""
        ledger = cls(keywords=list(keywords))
        for ks_id, kw in ledger._by_id.items():
            ledger._baseline_mode[int(ks_id)] = kw.keyword_setting.strategy_mode
        return ledger

    def _keyword_text(self, ks_id: int) -> str:
        kw = self._by_id.get(ks_id)
        return kw.text if kw is not None else ""

    def _set_keyword_mode(
        self,
        ks_id: int,
        new_mode: KeywordStrategyMode,
        *,
        new_hard_status: int | None = None,
    ) -> None:
        """Обновить DTO in-memory (``strategy_mode`` + согласованный ``hard_status``)."""
        kw = self._by_id.get(ks_id)
        if kw is None:
            return
        hs = (
            new_hard_status
            if new_hard_status is not None
            else hard_status_for_strategy_mode(new_mode)
        )
        new_ks = kw.keyword_setting.model_copy(
            update={"strategy_mode": new_mode, "hard_status": hs}
        )
        updated = kw.model_copy(update={"keyword_setting": new_ks})
        for idx, item in enumerate(self.keywords):
            if item.keyword_setting_original_id == ks_id:
                self.keywords[idx] = updated
                break
        self._by_id[ks_id] = updated

    def _record_applied(
        self,
        *,
        action: V3ActionType,
        ks_id: int,
        from_mode: KeywordStrategyMode,
        to_mode: KeywordStrategyMode,
        reason: str,
    ) -> None:
        self._last_reason[ks_id] = reason
        self._netto_action_type[ks_id] = action
        self._tick_applied.append(
            AppliedV3Action(
                action=action,
                keyword_setting_id=ks_id,
                keyword_text=self._keyword_text(ks_id),
                from_mode=from_mode,
                to_mode=to_mode,
                reason=reason,
            )
        )

    def apply_in_memory(self, actions: list[V3Action]) -> int:
        """Применить действия к in-memory DTO (без БД). Возвращает число успешных мутаций."""
        if not actions:
            return 0
        applied_count = 0
        ordered = sorted(
            actions, key=lambda a: V3_ACTION_APPLY_ORDER.get(a.action, 99)
        )
        for action in ordered:
            if action.action == V3ActionType.DO_NOTHING:
                continue
            if action.action == V3ActionType.REBALANCE_TRANSFER:
                if self._apply_transfer_in_memory(action):
                    applied_count += 1
                continue
            if action.keyword_setting_id is None:
                continue
            ks_id = int(action.keyword_setting_id)
            kw = self._by_id.get(ks_id)
            if kw is None:
                continue
            current = kw.keyword_setting.strategy_mode
            hard_status = kw.keyword_setting.hard_status

            if action.action == V3ActionType.UP:
                if not hard_status_allows_up(hard_status):
                    continue
                nxt = resolve_v3_action_target_mode(action, current)
                if nxt is None:
                    continue
                self._set_keyword_mode(ks_id, nxt)
                self._record_applied(
                    action=V3ActionType.UP,
                    ks_id=ks_id,
                    from_mode=current,
                    to_mode=nxt,
                    reason=action.reason,
                )
                applied_count += 1
            elif action.action == V3ActionType.DOWN:
                if int(hard_status) != _HARD_STATUS_WHITE_LIST:
                    continue
                nxt = resolve_v3_action_target_mode(action, current)
                if nxt is None:
                    continue
                self._set_keyword_mode(ks_id, nxt)
                self._record_applied(
                    action=V3ActionType.DOWN,
                    ks_id=ks_id,
                    from_mode=current,
                    to_mode=nxt,
                    reason=action.reason,
                )
                applied_count += 1
            elif action.action == V3ActionType.FORCE_OFF:
                if current == KeywordStrategyMode.OFF:
                    continue
                if not hard_status_allows_force_off(hard_status):
                    continue
                self._set_keyword_mode(ks_id, KeywordStrategyMode.OFF)
                self._record_applied(
                    action=V3ActionType.FORCE_OFF,
                    ks_id=ks_id,
                    from_mode=current,
                    to_mode=KeywordStrategyMode.OFF,
                    reason=action.reason,
                )
                applied_count += 1
        return applied_count

    def _apply_transfer_in_memory(self, action: V3Action) -> bool:
        """REBALANCE_TRANSFER: down source + up target in-memory."""
        if action.from_keyword_setting_id is None or action.to_keyword_setting_id is None:
            return False
        from_id = int(action.from_keyword_setting_id)
        to_id = int(action.to_keyword_setting_id)
        kw_from = self._by_id.get(from_id)
        kw_to = self._by_id.get(to_id)
        if kw_from is None or kw_to is None:
            return False
        mode_from = kw_from.keyword_setting.strategy_mode
        mode_to = kw_to.keyword_setting.strategy_mode
        hs_from = kw_from.keyword_setting.hard_status
        hs_to = kw_to.keyword_setting.hard_status
        if int(hs_from) != _HARD_STATUS_WHITE_LIST:
            return False
        if not hard_status_allows_up(hs_to):
            return False
        if mode_from == KeywordStrategyMode.OFF:
            return False
        down = step_down(mode_from)
        up = step_up(mode_to)
        if down is None or up is None:
            return False
        if mode_to != KeywordStrategyMode.OFF:
            return False
        if up != KeywordStrategyMode.MIN_CPA:
            return False
        self._set_keyword_mode(from_id, down)
        self._record_applied(
            action=V3ActionType.DOWN,
            ks_id=from_id,
            from_mode=mode_from,
            to_mode=down,
            reason=action.reason,
        )
        self._set_keyword_mode(to_id, up)
        self._record_applied(
            action=V3ActionType.REBALANCE_TRANSFER,
            ks_id=to_id,
            from_mode=mode_to,
            to_mode=up,
            reason=action.reason,
        )
        return True

    def _netto_changes(self) -> dict[int, KeywordStrategyMode]:
        """``ks_id`` → желаемый ``strategy_mode``, если отличается от baseline тика."""
        out: dict[int, KeywordStrategyMode] = {}
        for ks_id, baseline in self._baseline_mode.items():
            kw = self._by_id.get(ks_id)
            if kw is None:
                continue
            desired = kw.keyword_setting.strategy_mode
            if desired != baseline:
                out[ks_id] = desired
        return out

    @staticmethod
    def _action_type_for_netto(
        db_current: KeywordStrategyMode,
        desired: KeywordStrategyMode,
    ) -> V3ActionType:
        if desired == KeywordStrategyMode.OFF and db_current != KeywordStrategyMode.OFF:
            return V3ActionType.FORCE_OFF
        if mode_level(desired) < mode_level(db_current):
            return V3ActionType.DOWN
        return V3ActionType.UP

    async def flush_to_db(self, complex_adv: ComplexAdv) -> bool:
        """Нетто-flush: один SELECT + точечные UPDATE только изменённых ключей.

        Returns:
            True, если хотя бы одна строка обновлена в БД.
        """
        netto = self._netto_changes()
        if not netto:
            return False

        ks_ids = list(netto.keys())
        db_applied: list[AppliedV3Action] = []

        async with sm(read_only=False) as session:
            rows = await self._fetch_keyword_rows(session, ks_ids)
            for ks_id, db_mode, db_hs, _text in rows:
                desired = netto.get(ks_id)
                if desired is None:
                    continue
                if not can_persist_netto_mode_change(db_mode, desired, db_hs):
                    logger.debug(
                        "v3 flush skip: id=%s db_mode=%s desired=%s hard_status=%s",
                        ks_id,
                        db_mode,
                        desired,
                        db_hs,
                    )
                    continue
                hs = hard_status_for_strategy_mode(desired)
                _ = await session.execute(
                    update(KeywordSetting)
                    .where(KeywordSetting.id == ks_id)
                    .values(strategy_mode=desired, hard_status=hs)
                )
                reason = self._last_reason.get(ks_id, "v3_tick_flush")
                action_type = self._netto_action_type.get(
                    ks_id,
                    self._action_type_for_netto(db_mode, desired),
                )
                db_applied.append(
                    AppliedV3Action(
                        action=action_type,
                        keyword_setting_id=ks_id,
                        keyword_text=self._keyword_text(ks_id),
                        from_mode=db_mode,
                        to_mode=desired,
                        reason=reason,
                    )
                )
            if db_applied:
                tick_order = {
                    item.keyword_setting_id: idx
                    for idx, item in enumerate(self._tick_applied)
                    if item.keyword_setting_id is not None
                }
                db_applied.sort(
                    key=lambda a: tick_order.get(a.keyword_setting_id, 10**9)
                )
                await session.commit()
            else:
                await session.rollback()

        adv = getattr(complex_adv, "adv_setting", None)
        if adv is not None and db_applied:
            await persist_last_applied_v3(cast(AdvSetting, adv), db_applied)
        return bool(db_applied)

    @staticmethod
    async def _fetch_keyword_rows(
        session: AsyncSession,
        ks_ids: list[int],
    ) -> list[tuple[int, KeywordStrategyMode, int, str]]:
        if not ks_ids:
            return []
        res = await session.execute(
            select(
                KeywordSetting.id,
                KeywordSetting.strategy_mode,
                KeywordSetting.hard_status,
                KeywordSetting.text,
            ).where(KeywordSetting.id.in_(ks_ids))
        )
        return [
            (int(row[0]), row[1], int(row[2]), str(row[3] or ""))
            for row in res.all()
        ]
