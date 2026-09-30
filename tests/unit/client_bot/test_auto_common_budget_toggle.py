"""Тесты UI: кнопка авторасчёта общего бюджета и handler toggle."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers import auto_common_budget_toggle
from app.client_bot.user_interface.services.total_spend_snapshot import (
    TotalSpendSnapshot,
)
from app.client_bot.user_interface.views import keyboards


class FakeSession:
    def __init__(self, adv: SimpleNamespace) -> None:
        self._adv = adv

    async def execute(self, *_args, **_kwargs):
        return None

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
        return FakeSession(self._adv)

    async def __aenter__(self):
        return FakeSession(self._adv)

    async def __aexit__(self, *_) -> None:
        return None


@pytest.mark.unit
def test_campaign_activity_keyboard_shows_auto_common_budget_toggle() -> None:
    adv = SimpleNamespace(
        id=1,
        use_common_budget=True,
        auto_common_budget=False,
    )
    keyboard = keyboards.get_campaign_activity_menu_keyboard(adv)
    texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert "Включить авторасчёт общего бюджета" in texts


@pytest.mark.asyncio
async def test_toggle_auto_common_budget_rerenders_menu(monkeypatch) -> None:
    adv = SimpleNamespace(
        id=1,
        use_common_budget=True,
        auto_common_budget=False,
        common_budget_daily_limit=0,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
    )
    monkeypatch.setattr(
        auto_common_budget_toggle,
        "sm",
        FakeSessionMaker(adv),
    )
    monkeypatch.setattr(
        auto_common_budget_toggle,
        "load_total_spend_snapshot",
        AsyncMock(return_value=TotalSpendSnapshot(0.0, 0.0)),
    )
    monkeypatch.setattr(
        auto_common_budget_toggle.messages,
        "CampaignActivityMenu",
        MagicMock(return_value=SimpleNamespace(text="menu text")),
    )
    monkeypatch.setattr(
        auto_common_budget_toggle.keyboards,
        "get_campaign_activity_menu_keyboard",
        MagicMock(return_value="keyboard"),
    )

    bot = AsyncMock()
    callback_query = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=10), message_id=20)
    )
    callback_data = SimpleNamespace(adv_setting_original_id=1, new_status=True)

    await auto_common_budget_toggle.toggle_auto_common_budget(
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
