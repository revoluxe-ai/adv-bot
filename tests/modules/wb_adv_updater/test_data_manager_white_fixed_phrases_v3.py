"""Unit tests: add_white/fixed_phrases передают strategy РК в V3 sync."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.const import ALWAYS_ON
from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.wb_adv_updater import data_manager


@pytest.fixture
def adv_v3_max() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 10
    adv.bot_active = True
    adv.strategy = Strategy.MAX_CONV
    return adv


@pytest.fixture
def session_cm(adv_v3_max: MagicMock) -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session.get = AsyncMock(return_value=adv_v3_max)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return session, cm


@pytest.mark.asyncio
async def test_add_white_phrases_passes_adv_strategy_to_v3_sync(
    adv_v3_max: MagicMock, session_cm: tuple[MagicMock, MagicMock]
) -> None:
    session, cm = session_cm
    existing = MagicMock(spec=KeywordSetting)
    existing.strategy_mode = KeywordStrategyMode.OFF

    execute_result = MagicMock()
    execute_result.scalar.return_value = existing
    session.execute.return_value = execute_result

    with (
        patch("app.modules.wb_adv_updater.data_manager._sm", return_value=cm),
        patch(
            "app.modules.wb_adv_updater.data_manager.sync_keyword_setting_mode_for_v3"
        ) as sync_mock,
    ):
        await data_manager.add_white_phrases(["kw"], adv_v3_max.id)

    sync_mock.assert_called_once()
    assert sync_mock.call_args.kwargs["adv_strategy"] == Strategy.MAX_CONV
    assert sync_mock.call_args.kwargs["hard_status_override"] == 2


@pytest.mark.asyncio
async def test_add_fixed_phrases_passes_adv_strategy_to_v3_sync(
    adv_v3_max: MagicMock, session_cm: tuple[MagicMock, MagicMock]
) -> None:
    session, cm = session_cm
    existing = MagicMock(spec=KeywordSetting)
    existing.strategy_mode = KeywordStrategyMode.OFF

    execute_result = MagicMock()
    execute_result.scalar.return_value = existing
    session.execute.return_value = execute_result

    with (
        patch("app.modules.wb_adv_updater.data_manager._sm", return_value=cm),
        patch(
            "app.modules.wb_adv_updater.data_manager.sync_keyword_setting_mode_for_v3"
        ) as sync_mock,
    ):
        await data_manager.add_fixed_phrases(["kw"], adv_v3_max.id)

    sync_mock.assert_called_once()
    assert sync_mock.call_args.kwargs["adv_strategy"] == Strategy.MAX_CONV
    assert sync_mock.call_args.kwargs["hard_status_override"] == ALWAYS_ON
