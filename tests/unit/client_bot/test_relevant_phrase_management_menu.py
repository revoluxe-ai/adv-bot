"""Тесты подменю управления релевантными и нерелевантными фразами."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle import (
    open_relevant_phrase_management_menu,
    toggle_auto_add_only_relevant_phrase,
)
from app.client_bot.user_interface.views.callbacks import (
    AddBlackPhrasesTemplates,
    AddRelevantPhraseTemplates,
    AddRelevantPhrases,
    Adv,
    ChangeAutoAddOnlyRelevantPhraseStatus,
    ManageRelevantAndNonRelevantPhrases,
)
from app.client_bot.user_interface.views.messages.main_adv_setting_menu.keyboard.keyboard import (
    get_adv_setting_keyboard,
    get_relevant_phrase_management_keyboard,
)
from app.client_bot.user_interface.views.messages.messages import (
    RelevantPhraseManagementMenuMessage,
)
from app.modules.common_slaves.wildberries.models import AdvSetting


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value

    def scalar_one(self) -> object:
        return self._value


class _FakeSession:
    def __init__(self, value: object) -> None:
        self.value = value
        self.updated = False
        self.committed = False

    async def execute(self, _stmt):
        return _FakeResult(self.value)

    async def commit(self) -> None:
        self.committed = True

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self, value: object) -> None:
        self.session = _FakeSession(value)

    def __call__(self, read_only: bool = False) -> _FakeSession:
        return self.session


@pytest.mark.unit
def test_main_menu_replaces_direct_toggle_with_navigation_button() -> None:
    adv = SimpleNamespace(
        id=1,
        adv_id=10,
        bot_active=False,
        auto_add_only_relevant_phrase=False,
        individual_keywords_target_place_mode=False,
        use_incremental_stats=False,
        updater_common_bid_in_search_adv_active_status=False,
        auto_update_target_place=False,
        orders_source_for_auto_mode=None,
        sales_predict_method=None,
        bidder_coroutine_type=None,
        auto_budget_watchdog_enabled=False,
        strategy=None,
        search_adv_id=None,
        name="Test",
        active_status="9",
        nmids=[],
        wb_cabinet_id=1,
        max_place=None,
        auto_update_strategy=True,
        target_price_for_order=None,
        plan_for_sales_for_day=None,
        max_price_for_order=None,
        rec_system_mode=False,
        bidder_for_auto=False,
        max_cpm=None,
    )
    wb_user_cabinet = SimpleNamespace(id=11)
    markup = get_adv_setting_keyboard(wb_user_cabinet, adv, False)
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert "Управление релевантными и нерелевантными фразами" in texts
    assert "Включить добавление только релевантных фраз" not in texts
    parsed = ManageRelevantAndNonRelevantPhrases.unpack(
        next(
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.text == "Управление релевантными и нерелевантными фразами"
        )
    )
    assert parsed.adv_setting_original_id == 1


@pytest.mark.unit
def test_relevant_phrase_menu_false_state_has_default_workflow_only() -> None:
    adv = SimpleNamespace(id=1, adv_id=10, auto_add_only_relevant_phrase=False)
    markup = get_relevant_phrase_management_keyboard(adv)
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert texts == [
        "Включить добавление только релевантных фраз",
        "Добавить НЕРЕЛЕВАНТНЫЕ фразы",
        "Шаблоны нерелевантных фраз",
        "Назад в меню",
    ]
    assert "Добавить РЕЛЕВАНТНЫЕ фразы" not in texts
    assert "Шаблоны релевантных фраз" not in texts
    assert ChangeAutoAddOnlyRelevantPhraseStatus.unpack(
        markup.inline_keyboard[0][0].callback_data
    ).new_status is True
    assert AddBlackPhrasesTemplates.unpack(markup.inline_keyboard[1][0].callback_data).adv_setting_id == 1
    assert AddBlackPhrasesTemplates.unpack(markup.inline_keyboard[2][0].callback_data).adv_setting_id == 1
    assert Adv.unpack(markup.inline_keyboard[3][0].callback_data).adv_original_id == 1


@pytest.mark.unit
def test_relevant_phrase_menu_true_state_has_relevant_workflow_only() -> None:
    adv = SimpleNamespace(id=1, adv_id=10, auto_add_only_relevant_phrase=True)
    markup = get_relevant_phrase_management_keyboard(adv)
    texts = [button.text for row in markup.inline_keyboard for button in row]
    assert texts == [
        "Выключить добавление только релевантных фраз",
        "Добавить РЕЛЕВАНТНЫЕ фразы",
        "Шаблоны релевантных фраз",
        "Назад в меню",
    ]
    assert "Добавить НЕРЕЛЕВАНТНЫЕ фразы" not in texts
    assert "Шаблоны нерелевантных фраз" not in texts
    assert ChangeAutoAddOnlyRelevantPhraseStatus.unpack(
        markup.inline_keyboard[0][0].callback_data
    ).new_status is False
    assert AddRelevantPhrases.unpack(markup.inline_keyboard[1][0].callback_data).adv_setting_id == 1
    assert AddRelevantPhraseTemplates.unpack(markup.inline_keyboard[2][0].callback_data).adv_setting_id == 1
    assert Adv.unpack(markup.inline_keyboard[3][0].callback_data).adv_original_id == 1


@pytest.mark.asyncio
async def test_open_menu_does_not_toggle_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    adv = SimpleNamespace(
        id=1,
        adv_id=10,
        auto_add_only_relevant_phrase=False,
        card_ab_hold_mode=None,
    )
    fake_factory = _FakeSessionFactory(adv)
    monkeypatch.setattr(
        "app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle.sm",
        fake_factory,
    )

    rendered: dict[str, object] = {}

    class _Message:
        def __init__(self, bot, chat_id, adv_obj) -> None:
            rendered["chat_id"] = chat_id
            rendered["adv_obj"] = adv_obj

        async def __call__(self) -> None:
            rendered["called"] = True

    monkeypatch.setattr(
        "app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle.RelevantPhraseManagementMenuMessage",
        _Message,
    )
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=77)),
        from_user=SimpleNamespace(id=88),
    )
    data = ManageRelevantAndNonRelevantPhrases(adv_setting_original_id=1)
    await open_relevant_phrase_management_menu(callback, data, bot=AsyncMock())
    assert rendered["called"] is True
    assert rendered["chat_id"] == 77
    assert rendered["adv_obj"] is adv
    assert fake_factory.session.committed is False


@pytest.mark.asyncio
async def test_toggle_rerenders_menu_after_write(monkeypatch: pytest.MonkeyPatch) -> None:
    adv = SimpleNamespace(
        id=1,
        adv_id=10,
        auto_add_only_relevant_phrase=False,
        card_ab_hold_mode=None,
    )
    fake_factory = _FakeSessionFactory(adv)
    fake_factory.session.value = adv
    monkeypatch.setattr(
        "app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle.sm",
        fake_factory,
    )

    sent_messages: list[str] = []
    bot = AsyncMock()

    async def _send_message(chat_id: int, text: str, **kwargs) -> None:
        sent_messages.append(text)

    bot.send_message.side_effect = _send_message

    rendered: dict[str, object] = {}

    class _Message:
        def __init__(self, bot_obj, chat_id, adv_obj) -> None:
            rendered["chat_id"] = chat_id
            rendered["adv_obj"] = adv_obj

        async def __call__(self) -> None:
            rendered["called"] = True

    monkeypatch.setattr(
        "app.client_bot.user_interface.handlers.auto_add_only_relevant_phrase_toggle.RelevantPhraseManagementMenuMessage",
        _Message,
    )
    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=77)),
        from_user=SimpleNamespace(id=88),
    )
    data = ChangeAutoAddOnlyRelevantPhraseStatus(
        adv_id=10,
        wb_user_cabinet_original_id=0,
        new_status=True,
    )
    await toggle_auto_add_only_relevant_phrase(callback, data, bot=bot)
    assert sent_messages == ["Включено добавление только релевантных фраз"]
    assert rendered["called"] is True
    assert rendered["chat_id"] == 77
    assert rendered["adv_obj"] is adv
