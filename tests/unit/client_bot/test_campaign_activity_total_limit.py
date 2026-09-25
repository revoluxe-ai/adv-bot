"""Unit-тесты хендлеров абсолютного (lifetime) лимита бюджета РК.

Проверяют маппинг «вид лимита + цель → колонка ``AdvSetting``» и то, что
суточные лимиты при работе с абсолютным не затрагиваются.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.user_interface.handlers import campaign_activity
from app.shared.domains.wb.enums import AdvType

# Явный маркер: в этом каталоге авто-маркировка по пути не попадает в `-m unit`.
pytestmark = pytest.mark.unit


class _FakeSession:
    def __init__(self, adv: SimpleNamespace) -> None:
        self._adv = adv
        self.committed = False

    async def get(self, _model, _id):
        return self._adv

    async def commit(self) -> None:
        self.committed = True


class _FakeSessionMaker:
    def __init__(self, adv: SimpleNamespace) -> None:
        self.session = _FakeSession(adv)

    def __call__(self, *_, **__):
        return self

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_) -> None:
        return None


def _adv_setting() -> SimpleNamespace:
    return SimpleNamespace(
        id=1,
        name="РК-1",
        use_common_budget=False,
        auto_budget_daily_limit=100,
        search_auto_budget_daily_limit=100,
        common_budget_daily_limit=100,
        auto_budget_total_limit=0,
        search_auto_budget_total_limit=0,
        common_budget_total_limit=0,
    )


@pytest.fixture
def _stub_total_spend_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.client_bot.user_interface.services.total_spend_snapshot import (
        TotalSpendSnapshot,
    )

    monkeypatch.setattr(
        campaign_activity,
        "load_total_spend_snapshot",
        AsyncMock(return_value=TotalSpendSnapshot(0.0, 0.0)),
    )


@pytest.fixture
def _stub_messages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Сообщения — no-op: тесты проверяют запись в БД, не рендеринг."""
    monkeypatch.setattr(
        campaign_activity.messages,
        "CampaignActivityTargetMenu",
        MagicMock(return_value=AsyncMock()),
    )
    monkeypatch.setattr(
        campaign_activity.messages,
        "CampaignActivityChangeLimit",
        MagicMock(return_value=AsyncMock()),
    )


@pytest.mark.parametrize(
    ("campaign_type", "scope", "expected_attr"),
    [
        (None, "daily", "common_budget_daily_limit"),
        (AdvType.AUTO, "daily", "auto_budget_daily_limit"),
        (AdvType.SEARCH, "daily", "search_auto_budget_daily_limit"),
        (None, "total", "common_budget_total_limit"),
        (AdvType.AUTO, "total", "auto_budget_total_limit"),
        (AdvType.SEARCH, "total", "search_auto_budget_total_limit"),
    ],
)
def test_limit_attr_name_matrix(
    campaign_type: AdvType | None, scope: str, expected_attr: str
) -> None:
    assert campaign_activity._limit_attr_name(campaign_type, scope) == expected_attr


def test_limit_attr_name_rejects_unknown_scope() -> None:
    with pytest.raises(ValueError):
        campaign_activity._limit_attr_name(AdvType.AUTO, "weekly")


@pytest.mark.parametrize(
    ("campaign_type", "expected_attr"),
    [
        (None, "common_budget_total_limit"),
        (AdvType.AUTO, "auto_budget_total_limit"),
        (AdvType.SEARCH, "search_auto_budget_total_limit"),
    ],
)
@pytest.mark.asyncio
async def test_set_new_limit_writes_total_limit(
    monkeypatch: pytest.MonkeyPatch,
    _stub_messages: None,
    _stub_total_spend_loader: None,
    campaign_type: AdvType | None,
    expected_attr: str,
) -> None:
    """``scope="total"`` пишет в абсолютную колонку, суточные не меняются."""
    adv = _adv_setting()
    session_maker = _FakeSessionMaker(adv)
    monkeypatch.setattr(campaign_activity, "sm", session_maker)

    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={
            "adv_setting_id": 1,
            "campaign_type": campaign_type.value if campaign_type else None,
            "scope": "total",
        }
    )
    message = SimpleNamespace(
        text="750",
        bot=MagicMock(),
        chat=SimpleNamespace(id=10),
        answer=AsyncMock(),
    )

    await campaign_activity.set_new_limit(message, state)

    assert getattr(adv, expected_attr) == 750
    assert adv.auto_budget_daily_limit == 100
    assert adv.search_auto_budget_daily_limit == 100
    assert adv.common_budget_daily_limit == 100
    assert session_maker.session.committed is True
    state.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_new_limit_defaults_to_daily_scope(
    monkeypatch: pytest.MonkeyPatch,
    _stub_messages: None,
    _stub_total_spend_loader: None,
) -> None:
    """Без ``scope`` в данных FSM редактируется суточный лимит (обратная совместимость)."""
    adv = _adv_setting()
    monkeypatch.setattr(campaign_activity, "sm", _FakeSessionMaker(adv))

    state = AsyncMock()
    state.get_data = AsyncMock(
        return_value={"adv_setting_id": 1, "campaign_type": AdvType.AUTO.value}
    )
    message = SimpleNamespace(
        text="900",
        bot=MagicMock(),
        chat=SimpleNamespace(id=10),
        answer=AsyncMock(),
    )

    await campaign_activity.set_new_limit(message, state)

    assert adv.auto_budget_daily_limit == 900
    assert adv.auto_budget_total_limit == 0


@pytest.mark.asyncio
async def test_turn_off_total_limit_writes_zero(
    monkeypatch: pytest.MonkeyPatch,
    _stub_messages: None,
    _stub_total_spend_loader: None,
) -> None:
    """«Убрать лимит» на экране абсолютного лимита пишет 0 только в него."""
    adv = _adv_setting()
    adv.auto_budget_total_limit = 500
    session_maker = _FakeSessionMaker(adv)
    monkeypatch.setattr(campaign_activity, "sm", session_maker)

    callback = SimpleNamespace(
        message=SimpleNamespace(chat=SimpleNamespace(id=10)),
        bot=MagicMock(),
    )
    callback_data = SimpleNamespace(
        adv_setting_original_id=1,
        campaign_type=AdvType.AUTO,
        scope="total",
    )

    await campaign_activity.turn_off_limit(callback, callback_data)

    assert adv.auto_budget_total_limit == 0
    assert adv.auto_budget_daily_limit == 100
    assert session_maker.session.committed is True


def test_total_limit_display_zero_is_no_limit() -> None:
    """В сводке меню абсолютный 0 показывается как «нет лимита», не «выключено»."""
    from app.client_bot.user_interface.views.messages import messages as msg

    assert msg._total_limit_display(0) == "нет лимита"
    assert msg._total_limit_display(500) == "500 руб всего"


def test_total_limit_target_menu_copy_says_no_limit() -> None:
    """Экран абсолютного лимита при 0: «нет лимита», без пауза-формулировок."""
    from app.client_bot.user_interface.views.messages.messages import (
        CampaignActivityTargetMenu,
    )

    adv = _adv_setting()
    menu = CampaignActivityTargetMenu(
        bot=MagicMock(),
        chat_id=1,
        adv_setting=adv,  # type: ignore[arg-type]
        campaign_type=AdvType.AUTO,
        current_limit=0,
        scope="total",
    )
    text = menu.text
    assert "нет лимита" in text
    assert "выключено" not in text
    assert "не паузится" in text


def test_daily_limit_target_menu_zero_still_says_off() -> None:
    """Суточный 0 по-прежнему «выключено» — семантика daily не меняется."""
    from app.client_bot.user_interface.views.messages.messages import (
        CampaignActivityTargetMenu,
    )

    adv = _adv_setting()
    menu = CampaignActivityTargetMenu(
        bot=MagicMock(),
        chat_id=1,
        adv_setting=adv,  # type: ignore[arg-type]
        campaign_type=AdvType.AUTO,
        current_limit=0,
        scope="daily",
    )
    text = menu.text
    assert "выключено" in text
    assert "нет лимита" not in text
    assert "Расход Авто за всё время" not in text


def test_total_limit_target_menu_shows_three_spend_lines() -> None:
    from app.client_bot.user_interface.services.total_spend_snapshot import (
        TotalSpendSnapshot,
    )
    from app.client_bot.user_interface.views.messages.messages import (
        CampaignActivityTargetMenu,
    )

    adv = _adv_setting()
    snap = TotalSpendSnapshot(auto=100.2, search=50.1)
    menu = CampaignActivityTargetMenu(
        bot=MagicMock(),
        chat_id=1,
        adv_setting=adv,  # type: ignore[arg-type]
        campaign_type=AdvType.AUTO,
        current_limit=500,
        scope="total",
        total_spend=snap,
    )
    text = menu.text
    assert "101 р." in text
    assert "51 р." in text
    assert "151 р." in text
    assert "← для этого лимита" in text
    assert "Лимит должен быть больше расхода" in text


def test_activity_menu_shows_spend_even_when_limit_zero() -> None:
    from app.client_bot.user_interface.services.total_spend_snapshot import (
        TotalSpendSnapshot,
    )
    from app.client_bot.user_interface.views.messages.messages import (
        CampaignActivityMenu,
    )

    adv = _adv_setting()
    menu = CampaignActivityMenu(
        bot=MagicMock(),
        chat_id=1,
        adv_setting=adv,  # type: ignore[arg-type]
        total_spend=TotalSpendSnapshot(auto=10.0, search=0.0),
    )
    text = menu.text
    assert "Расход Авто за всё время" in text
    assert "Расход Аукцион за всё время" in text
    assert "Расход Авто+Аукцион за всё время" in text


def test_total_spend_unknown_shows_nd_in_ui() -> None:
    from app.client_bot.user_interface.services.total_spend_snapshot import (
        TotalSpendSnapshot,
    )
    from app.client_bot.user_interface.views.messages.messages import (
        CampaignActivityMenu,
    )

    adv = _adv_setting()
    menu = CampaignActivityMenu(
        bot=MagicMock(),
        chat_id=1,
        adv_setting=adv,  # type: ignore[arg-type]
        total_spend=TotalSpendSnapshot(auto=None, search=0.0),
    )
    assert "н/д" in menu.text


def test_daily_limit_change_screen_has_no_spend_lines() -> None:
    from app.client_bot.user_interface.views.messages.messages import (
        CampaignActivityChangeLimit,
    )

    menu = CampaignActivityChangeLimit(
        bot=MagicMock(),
        chat_id=1,
        campaign_type=AdvType.AUTO,
        scope="daily",
    )
    assert "Расход Авто за всё время" not in menu.text


def test_total_limit_keyboard_clear_button_label() -> None:
    """Кнопка сброса абсолютного лимита — «Убрать лимит», не «Выключить»."""
    from app.client_bot.user_interface.views import keyboards

    adv = _adv_setting()
    adv.id = 1
    markup = keyboards.get_campaign_activity_target_keyboard(
        adv,  # type: ignore[arg-type]
        AdvType.AUTO,
        current_limit=500,
        scope="total",
    )
    texts = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "Убрать лимит" in texts
    assert "Выключить" not in texts


def test_daily_limit_keyboard_still_says_turn_off() -> None:
    """Кнопка сброса суточного лимита остаётся «Выключить»."""
    from app.client_bot.user_interface.views import keyboards

    adv = _adv_setting()
    adv.id = 1
    markup = keyboards.get_campaign_activity_target_keyboard(
        adv,  # type: ignore[arg-type]
        AdvType.AUTO,
        current_limit=500,
        scope="daily",
    )
    texts = [btn.text for row in markup.inline_keyboard for btn in row]
    assert "Выключить" in texts
    assert "Убрать лимит" not in texts
