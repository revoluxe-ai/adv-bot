import pytest
from unittest.mock import AsyncMock, MagicMock


pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class MockSessionMaker:
    """Async context manager-обёртка, совместимая с паттерном: `async with sm(...) as session:`"""

    def __init__(self, session):
        self._session = session

    def __call__(self, read_only=False):  # noqa: ARG002
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):  # noqa: D401, ANN001
        return None


async def test_apply_default_settings_to_adv_calls_defaults_and_commit(mocker):
    from app.modules.adv_creator.backend.main_manager import MainAdvManager

    adv_id = 123

    # --- session.execute(...).scalar_one() -> adv_setting ---
    wb_cabinet_mock = MagicMock(name="wb_cabinet")
    adv_setting_mock = MagicMock(name="adv_setting")
    adv_setting_mock.wb_cabinet = wb_cabinet_mock

    result_mock = MagicMock(name="result")
    result_mock.scalar_one.return_value = adv_setting_mock

    session_mock = MagicMock(name="session")
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.commit = AsyncMock()

    # Патчим session maker и apply_new_campaign_free_defaults по месту использования.
    apply_defaults_mock = mocker.patch(
        "app.modules.adv_creator.backend.main_manager.apply_new_campaign_free_defaults"
    )
    mocker.patch(
        "app.modules.adv_creator.backend.main_manager.sm",
        MockSessionMaker(session_mock),
    )

    await MainAdvManager._apply_default_settings_to_adv(adv_id)

    # execute вызван один раз с каким-то SQLAlchemy stmt
    assert session_mock.execute.call_count == 1

    apply_defaults_mock.assert_called_once_with(adv_setting_mock, wb_cabinet_mock)
    session_mock.commit.assert_awaited_once()
