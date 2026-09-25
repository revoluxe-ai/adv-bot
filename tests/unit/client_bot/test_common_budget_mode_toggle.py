from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers import common_budget_mode_toggle


class FakeSession:
    def __init__(
        self, adv: SimpleNamespace, executed: list[object] | None = None
    ) -> None:
        self._adv = adv
        self._executed = executed if executed is not None else []

    async def execute(self, *args, **_kwargs):
        if args:
            self._executed.append(args[0])
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
    def __init__(
        self, adv: SimpleNamespace, executed: list[object] | None = None
    ) -> None:
        self._adv = adv
        self.executed: list[object] = executed if executed is not None else []

    def __call__(self, *_, **__):
        return self

    async def __aenter__(self):
        return FakeSession(self._adv, self.executed)

    async def __aexit__(self, *_) -> None:
        return None


@pytest.mark.asyncio
async def test_toggle_common_budget_mode_rerenders_menu(monkeypatch) -> None:
    adv = SimpleNamespace(
        id=1,
        common_budget_daily_limit=0,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
        common_budget_total_limit=0,
        auto_budget_total_limit=0,
        search_auto_budget_total_limit=0,
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


@pytest.mark.unit
@pytest.mark.parametrize("new_status", [True, False])
@pytest.mark.asyncio
async def test_toggle_common_budget_mode_does_not_touch_total_limits(
    monkeypatch, new_status: bool
) -> None:
    """Переключение режима пересчитывает только суточные лимиты.

    Абсолютные лимиты сознательно не миграруются между режимами: авторасчёт мог
    бы молча удвоить лимит или, наоборот, поставить РК на паузу.
    """
    adv = SimpleNamespace(
        id=1,
        common_budget_daily_limit=300,
        auto_budget_daily_limit=0,
        search_auto_budget_daily_limit=0,
        common_budget_total_limit=500,
        auto_budget_total_limit=500,
        search_auto_budget_total_limit=500,
    )
    session_maker = FakeSessionMaker(adv)
    monkeypatch.setattr(common_budget_mode_toggle, "sm", session_maker)
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

    callback_query = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=10), message_id=20)
    )
    await common_budget_mode_toggle.toggle_common_budget_mode(
        callback_query=callback_query,
        callback_data=SimpleNamespace(adv_setting_original_id=1, new_status=new_status),
        bot=AsyncMock(),
    )

    updates = [
        str(stmt)
        for stmt in session_maker.executed
        if str(stmt).strip().upper().startswith("UPDATE")
    ]
    assert updates, "ожидался UPDATE advsetting при переключении режима"
    for statement in updates:
        assert "total_limit" not in statement
