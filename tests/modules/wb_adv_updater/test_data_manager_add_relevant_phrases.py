"""Unit tests: ``add_relevant_phrases`` не сбрасывает лестницу V3 у существующих ключей БС."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.wb_adv_updater import data_manager


@pytest.fixture
def adv_v3() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 10
    adv.bot_active = True
    return adv


@pytest.fixture
def session_cm(adv_v3: MagicMock) -> tuple[MagicMock, MagicMock]:
    session = MagicMock()
    session.get = AsyncMock(return_value=adv_v3)
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    return session, cm


@pytest.mark.asyncio
async def test_add_relevant_phrases_keeps_v3_ladder_on_white_list(
    adv_v3: MagicMock, session_cm: tuple[MagicMock, MagicMock]
) -> None:
    session, cm = session_cm
    existing = MagicMock(spec=KeywordSetting)
    existing.hard_status = 2
    existing.strategy_mode = KeywordStrategyMode.OPTIMUM
    existing.relevant = False

    execute_result = MagicMock()
    execute_result.scalar.return_value = existing
    session.execute.return_value = execute_result

    with (
        patch("app.modules.wb_adv_updater.data_manager._sm", return_value=cm),
        patch(
            "app.modules.wb_adv_updater.data_manager.sync_keyword_setting_mode_for_v3"
        ) as sync_mock,
    ):
        await data_manager.add_relevant_phrases(["foo"], adv_v3.id)

    assert existing.relevant is True
    sync_mock.assert_not_called()


@pytest.mark.asyncio
async def test_add_relevant_phrases_syncs_new_keyword_for_v3(
    adv_v3: MagicMock, session_cm: tuple[MagicMock, MagicMock]
) -> None:
    session, cm = session_cm
    execute_result = MagicMock()
    execute_result.scalar.return_value = None
    session.execute.return_value = execute_result

    with (
        patch("app.modules.wb_adv_updater.data_manager._sm", return_value=cm),
        patch(
            "app.modules.wb_adv_updater.data_manager.sync_keyword_setting_mode_for_v3"
        ) as sync_mock,
    ):
        await data_manager.add_relevant_phrases(["new_kw"], adv_v3.id)

    sync_mock.assert_called_once()
    session.add.assert_called_once()
