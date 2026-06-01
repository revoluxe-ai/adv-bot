"""Unit-тесты записи последнего V3-действия в Redis из applier."""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    apply_v3_actions,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from tests.unit.test_auto_updater_v3_applier import _patched_sm


def _make_result(row: tuple[KeywordStrategyMode, int] | None) -> MagicMock:
    result = MagicMock()
    result.one_or_none.return_value = row
    return result


def _make_scalar_result(text: str | None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = text
    return result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_writes_redis_on_successful_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_set = AsyncMock()
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.LastV3UpdaterActionRedisCache.set",
        redis_set,
    )

    async def _execute(stmt: object) -> MagicMock:
        sql = str(stmt)
        if sql.startswith("SELECT"):
            if "text" in sql.lower():
                return _make_scalar_result("мой ключ")
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

    adv = MagicMock()
    adv.adv_id = 100
    complex_adv = MagicMock()
    complex_adv.adv_setting = adv
    await apply_v3_actions(
        [V3Action(action=V3ActionType.UP, keyword_setting_id=1, reason="test")],
        complex_adv=cast(MagicMock, complex_adv),
    )
    redis_set.assert_awaited_once()
    snapshot = redis_set.call_args[0][0]
    assert snapshot.action == V3ActionType.UP
    assert snapshot.keyword_text == "мой ключ"
    assert snapshot.from_mode == "OFF"
    assert snapshot.to_mode == "MIN_CPA"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_skipped_up_does_not_write_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_set = AsyncMock()
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.LastV3UpdaterActionRedisCache.set",
        redis_set,
    )

    async def _execute(stmt: object) -> MagicMock:
        if str(stmt).startswith("SELECT"):
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

    adv = MagicMock()
    complex_adv = MagicMock()
    complex_adv.adv_setting = adv
    await apply_v3_actions(
        [V3Action(action=V3ActionType.UP, keyword_setting_id=1, reason="test")],
        complex_adv=cast(MagicMock, complex_adv),
    )
    redis_set.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_apply_do_nothing_does_not_write_redis(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis_set = AsyncMock()
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3.applier.LastV3UpdaterActionRedisCache.set",
        redis_set,
    )
    adv = MagicMock()
    complex_adv = MagicMock()
    complex_adv.adv_setting = adv
    await apply_v3_actions(
        [V3Action(action=V3ActionType.DO_NOTHING, reason="idle")],
        complex_adv=cast(MagicMock, complex_adv),
    )
    redis_set.assert_not_awaited()
