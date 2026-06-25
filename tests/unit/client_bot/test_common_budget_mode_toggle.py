from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers import common_budget_mode_toggle


class FakeSession:
    def __init__(self, adv: SimpleNamespace) -> None:
        self._adv = adv

    async def execute(self, *_args, **_kwargs):
        return SimpleNamespace(scalar_one_or_none=lambda: self._adv)

    async def commit(self) -> None:
        return None

    async def get(self, _model, _id):
        return self._adv

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_) -> None:
        return None


class FakeSessionMaker:
    def __init__(self, adv: SimpleNamespace) -> None:
        self._adv = adv

    def __call__(self, *_, **__):
        return self

    async def __aenter__(self):
        return FakeSession(self._adv)

    async def __aexit__(self, *_) -> None:
        return None


@pytest.mark.asyncio
async def test_toggle_common_budget_mode_rerenders_menu(monkeypatch) -> None:
    adv = SimpleNamespace(
        id=1,
        common_budget_daily_limit=0,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
    )
    monkeypatch.setattr(
        common_budget_mode_toggle,
        "sm",
        FakeSessionMaker(adv),
    )
    monkeypatch.setattr(
        common_budget_mode_toggle.messages,
        "CampaignActivityMenu",
        MagicMock(return_value=SimpleNamespace(text="menu text")),
    )
    monkeypatch.setattr(
        common_budget_mode_toggle.keyboards,
        "get_campaign_activity_menu_keyboard",
        MagicMock(return_value="keyboard"),
    )

    bot = AsyncMock()
    callback_query = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=10), message_id=20)
    )
    callback_data = SimpleNamespace(adv_setting_original_id=1, new_status=True)

    await common_budget_mode_toggle.toggle_common_budget_mode(
        callback_query=callback_query,
        callback_data=callback_data,
        bot=bot,
    )

    bot.edit_message_text.assert_awaited_once_with(
        chat_id=10,
        message_id=20,
        text="menu text",
        reply_markup="keyboard",
    )
