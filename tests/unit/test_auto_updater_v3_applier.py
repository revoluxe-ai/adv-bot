from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    apply_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)


def _patched_sm(session_cm: AsyncMock) -> Callable[..., AsyncMock]:
    def _open(*_a: object, **_k: object) -> AsyncMock:
        return session_cm

    return _open


def _update_stmts_from_execute(execute_mock: AsyncMock) -> list[object]:
    out: list[object] = []
    for call in execute_mock.call_args_list:
        if not call.args:
            continue
        stmt = cast(object, call.args[0])
        if str(stmt).startswith("UPDATE"):
            out.append(stmt)
    return out


def _make_result(row: tuple[KeywordStrategyMode, int] | None) -> MagicMock:
    result = MagicMock()
    result.one_or_none.return_value = row
    return result


def _update_bind_params(stmt: Any) -> dict[str, Any]:
    return dict(stmt.compile(dialect=postgresql.dialect()).params)


def _complex_adv_stub() -> MagicMock:
    adv = MagicMock()
    adv.adv_setting = None
    return adv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_actions_skips_up_when_hard_status_not_auto_or_white_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_sql: list[str] = []

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        executed_sql.append(sql)
        if sql.startswith("SELECT"):
            return _make_result((KeywordStrategyMode.OFF, 3))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [V3Action(action=V3ActionType.UP, keyword_setting_id=1, reason="test")],
        complex_adv=_complex_adv_stub(),
    )

    assert sum(1 for sql in executed_sql if sql.startswith("UPDATE")) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_actions_allows_up_when_hard_status_white_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        if sql.startswith("SELECT"):
            return _make_result((KeywordStrategyMode.OFF, 2))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [V3Action(action=V3ActionType.UP, keyword_setting_id=1, reason="test")],
        complex_adv=_complex_adv_stub(),
    )

    update_stmts = _update_stmts_from_execute(session.execute)
    assert len(update_stmts) == 1
    params = _update_bind_params(update_stmts[0])
    assert params["strategy_mode"] == KeywordStrategyMode.MIN_CPA
    assert params["hard_status"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_actions_skips_down_when_hard_status_not_white_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_sql: list[str] = []

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        executed_sql.append(sql)
        if sql.startswith("SELECT"):
            return _make_result((KeywordStrategyMode.MIN_CPA, 1))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [V3Action(action=V3ActionType.DOWN, keyword_setting_id=1, reason="test")],
        complex_adv=_complex_adv_stub(),
    )

    assert sum(1 for sql in executed_sql if sql.startswith("UPDATE")) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_force_off_batch_sets_off_and_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_calls = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal select_calls
        sql = str(stmt)
        if sql.startswith("SELECT"):
            select_calls += 1
            mode = (
                KeywordStrategyMode.MAX_CONVERSION
                if select_calls == 1
                else KeywordStrategyMode.OPTIMUM
            )
            return _make_result((mode, 2))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [
            V3Action(action=V3ActionType.FORCE_OFF, keyword_setting_id=1, reason="t"),
            V3Action(action=V3ActionType.FORCE_OFF, keyword_setting_id=2, reason="t"),
        ],
        complex_adv=_complex_adv_stub(),
    )

    update_stmts = _update_stmts_from_execute(session.execute)
    assert len(update_stmts) == 2
    for stmt in update_stmts:
        params = _update_bind_params(stmt)
        assert params["strategy_mode"] == KeywordStrategyMode.OFF
        assert params["hard_status"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_down_to_off_sets_hard_status_auto(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        if sql.startswith("SELECT"):
            return _make_result((KeywordStrategyMode.MIN_CPA, 2))
        return MagicMock()

    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [V3Action(action=V3ActionType.DOWN, keyword_setting_id=1, reason="test")],
        complex_adv=_complex_adv_stub(),
    )

    update_stmts = _update_stmts_from_execute(session.execute)
    assert len(update_stmts) == 1
    params = _update_bind_params(update_stmts[0])
    assert params["strategy_mode"] == KeywordStrategyMode.OFF
    assert params["hard_status"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_down_uses_target_strategy_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AsyncMock()

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        if sql.startswith("SELECT"):
            return _make_result((KeywordStrategyMode.MAX_CONVERSION, 2))
        return MagicMock()

    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [
            V3Action(
                action=V3ActionType.DOWN,
                keyword_setting_id=1,
                target_strategy_mode=KeywordStrategyMode.MIN_CPA,
                reason="test_target_down",
            )
        ],
        complex_adv=_complex_adv_stub(),
    )

    update_stmts = _update_stmts_from_execute(session.execute)
    assert len(update_stmts) == 1
    params = _update_bind_params(update_stmts[0])
    assert params["strategy_mode"] == KeywordStrategyMode.MIN_CPA
    assert params["hard_status"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_transfer_sets_hard_status_on_both(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    select_calls = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal select_calls
        sql = str(stmt)
        if sql.startswith("SELECT"):
            select_calls += 1
            if select_calls == 1:
                return _make_result((KeywordStrategyMode.MIN_CPA, 2))
            return _make_result((KeywordStrategyMode.OFF, 1))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [
            V3Action(
                action=V3ActionType.REBALANCE_TRANSFER,
                from_keyword_setting_id=10,
                to_keyword_setting_id=20,
                reason="test",
            )
        ],
        complex_adv=_complex_adv_stub(),
    )

    update_stmts = _update_stmts_from_execute(session.execute)
    assert len(update_stmts) == 2
    from_params = _update_bind_params(update_stmts[0])
    to_params = _update_bind_params(update_stmts[1])
    assert from_params["strategy_mode"] == KeywordStrategyMode.OFF
    assert from_params["hard_status"] == 1
    assert to_params["strategy_mode"] == KeywordStrategyMode.MIN_CPA
    assert to_params["hard_status"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_transfer_skips_when_hard_status_pair_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executed_sql: list[str] = []
    select_calls = 0

    async def _execute(stmt: object) -> MagicMock:
        nonlocal select_calls
        sql = str(stmt)
        executed_sql.append(sql)
        if sql.startswith("SELECT"):
            select_calls += 1
            if select_calls == 1:
                return _make_result((KeywordStrategyMode.OPTIMUM, 2))
            return _make_result((KeywordStrategyMode.OFF, 3))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [
            V3Action(
                action=V3ActionType.REBALANCE_TRANSFER,
                from_keyword_setting_id=10,
                to_keyword_setting_id=20,
                reason="test",
            )
        ],
        complex_adv=_complex_adv_stub(),
    )

    assert sum(1 for sql in executed_sql if sql.startswith("UPDATE")) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_v3_jump_up_uses_target_strategy_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        if sql.startswith("SELECT"):
            return _make_result((KeywordStrategyMode.OFF, 2))
        return MagicMock()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=_execute)
    session.commit = AsyncMock()
    session_cm = AsyncMock()
    session_cm.__aenter__.return_value = session
    session_cm.__aexit__.return_value = None
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.sm",
        _patched_sm(session_cm),
    )

    await apply_v3_actions(
        [
            V3Action(
                action=V3ActionType.UP,
                keyword_setting_id=1,
                target_strategy_mode=KeywordStrategyMode.MAX_CONVERSION,
                reason="cost_first",
            )
        ],
        complex_adv=_complex_adv_stub(),
    )

    update_stmts = _update_stmts_from_execute(session.execute)
    assert len(update_stmts) == 1
    params = _update_bind_params(update_stmts[0])
    assert params["strategy_mode"] == KeywordStrategyMode.MAX_CONVERSION
    assert params["hard_status"] == 2

