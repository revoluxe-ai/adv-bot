"""Unit tests for data_manager update_black_phrases and reset_black_phrases."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater import data_manager


@pytest.fixture
def adv_setting_mock() -> MagicMock:
    adv = MagicMock(spec=AdvSetting)
    adv.id = 42
    adv.black_phrases = []
    return adv


@pytest.mark.asyncio
async def test_update_black_phrases_delegates_to_relevant_phrase_manager(
    adv_setting_mock: MagicMock,
) -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=adv_setting_mock)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    manager_instance = MagicMock()
    manager_instance.update_black_phrases = AsyncMock()

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            return_value=manager_instance,
        ),
    ):
        await data_manager.update_black_phrases(42, ["kw1", r"kw2|extra"])

    session.get.assert_called_once_with(AdvSetting, 42)
    manager_instance.update_black_phrases.assert_called_once_with(["kw1", r"kw2|extra"])


@pytest.mark.asyncio
async def test_update_black_phrases_returns_early_when_adv_not_found() -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            MagicMock(),
        ) as manager_cls,
    ):
        await data_manager.update_black_phrases(999, ["x"])

    manager_cls.assert_not_called()


@pytest.mark.asyncio
async def test_reset_black_phrases_delegates_to_relevant_phrase_manager(
    adv_setting_mock: MagicMock,
) -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=adv_setting_mock)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    manager_instance = MagicMock()
    manager_instance.update_black_phrases = AsyncMock()

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            return_value=manager_instance,
        ),
    ):
        await data_manager.reset_black_phrases(42)

    session.get.assert_called_once_with(AdvSetting, 42)
    manager_instance.update_black_phrases.assert_called_once_with([])


@pytest.mark.asyncio
async def test_reset_black_phrases_returns_early_when_adv_not_found() -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            MagicMock(),
        ) as manager_cls,
    ):
        await data_manager.reset_black_phrases(999)

    manager_cls.assert_not_called()


@pytest.mark.asyncio
async def test_update_relevant_phrases_templates_delegates_to_manager(
    adv_setting_mock: MagicMock,
) -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=adv_setting_mock)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    manager_instance = MagicMock()
    manager_instance.update_relevant_phrases_templates = AsyncMock()

    adv_setting_mock.relevant_phrases = []

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            return_value=manager_instance,
        ),
    ):
        await data_manager.update_relevant_phrases_templates(42, ["kw1", r"kw2"])

    session.get.assert_called_once_with(AdvSetting, 42)
    manager_instance.update_relevant_phrases_templates.assert_called_once_with(
        ["kw1", r"kw2"]
    )


@pytest.mark.asyncio
async def test_update_relevant_phrases_templates_returns_early_when_adv_not_found() -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=None)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            MagicMock(),
        ) as manager_cls,
    ):
        await data_manager.update_relevant_phrases_templates(999, ["x"])

    manager_cls.assert_not_called()


@pytest.mark.asyncio
async def test_reset_relevant_phrases_templates_delegates(
    adv_setting_mock: MagicMock,
) -> None:
    session = MagicMock()
    session.get = AsyncMock(return_value=adv_setting_mock)

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)
    sm_mock = MagicMock(return_value=cm)

    manager_instance = MagicMock()
    manager_instance.update_relevant_phrases_templates = AsyncMock()

    with (
        patch(
            "app.modules.wb_adv_updater.data_manager._sm",
            sm_mock,
        ),
        patch(
            "app.modules.wb_adv_updater.data_manager.RelevantPhraseManager",
            return_value=manager_instance,
        ),
    ):
        await data_manager.reset_relevant_phrases_templates(42)

    manager_instance.update_relevant_phrases_templates.assert_called_once_with([])
