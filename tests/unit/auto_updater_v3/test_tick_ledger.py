"""Unit: V3TickKeywordLedger — in-memory apply и нетто-flush."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger import (
    V3TickKeywordLedger,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def _kw(
    *,
    ks_id: int,
    mode: KeywordStrategyMode,
    hard_status: int = 2,
) -> CalculatedKeyword:
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=f"k{ks_id}",
            relevant=True,
            hard_status=hard_status,
            id=ks_id,
            strategy_mode=mode,
        ),
        cluster_stat=make_zero_keyword_stat(f"k{ks_id}"),
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=1.0,
        target_pay_for_order=None,
    )


def _patched_sm(session_cm: AsyncMock) -> Callable[..., AsyncMock]:
    def _open(*_a: object, **_k: object) -> AsyncMock:
        return session_cm

    return _open


def _update_stmts(execute_mock: AsyncMock) -> list[Any]:
    out: list[Any] = []
    for call in execute_mock.call_args_list:
        if call.args and str(call.args[0]).startswith("UPDATE"):
            out.append(call.args[0])
    return out


@pytest.mark.unit
def test_apply_in_memory_updates_dto_for_next_phase() -> None:
    """Phase0 меняет mode in-memory — следующая фаза видит новый strategy_mode."""
    kw = _kw(ks_id=10, mode=KeywordStrategyMode.OFF, hard_status=1)
    ledger = V3TickKeywordLedger.from_keywords([kw])
    ledger.apply_in_memory(
        [
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=10,
                target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                reason="no_data_min_bid",
            )
        ]
    )
    assert ledger.keywords[0].keyword_setting.strategy_mode == KeywordStrategyMode.MIN_CPA
    assert ledger.keywords[0].keyword_setting.hard_status == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_flush_skips_hard_status_not_auto_or_white_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kw = _kw(ks_id=5, mode=KeywordStrategyMode.OFF, hard_status=1)
    ledger = V3TickKeywordLedger.from_keywords([kw])
    ledger.apply_in_memory(
        [
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=5,
                target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                reason="test",
            )
        ]
    )

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        result = MagicMock()
        if sql.startswith("SELECT"):
            # Пользователь поставил always_on (4) во время тика
            result.all.return_value = [(5, KeywordStrategyMode.OFF, 4, "k5")]
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.sm",
        _patched_sm(session_cm),
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.persist_last_applied_v3",
        AsyncMock(),
    )

    flushed = await ledger.flush_to_db(MagicMock(adv_setting=MagicMock()))
    assert flushed is False
    assert _update_stmts(session.execute) == []
    session.rollback.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_flush_updates_only_strategy_mode_and_hard_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    kw = _kw(ks_id=7, mode=KeywordStrategyMode.MIN_CPA, hard_status=2)
    ledger = V3TickKeywordLedger.from_keywords([kw])
    ledger.apply_in_memory(
        [
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=7,
                target_strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                reason="m1_test",
            )
        ]
    )

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        result = MagicMock()
        if sql.startswith("SELECT"):
            result.all.return_value = [
                (7, KeywordStrategyMode.MIN_CPA, 2, "k7")
            ]
        return result

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.sm",
        _patched_sm(session_cm),
    )
    persist = AsyncMock()
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.tick_ledger.persist_last_applied_v3",
        persist,
    )

    flushed = await ledger.flush_to_db(MagicMock(adv_setting=MagicMock()))
    assert flushed is True
    updates = _update_stmts(session.execute)
    assert len(updates) == 1
    params = dict(
        updates[0].compile(dialect=postgresql.dialect()).params  # type: ignore[union-attr]
    )
    assert params["strategy_mode"] == KeywordStrategyMode.MAX_CONVERSION
    assert params["hard_status"] == 2
    session.commit.assert_awaited_once()
    persist.assert_awaited_once()
