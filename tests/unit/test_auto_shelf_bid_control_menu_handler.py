from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.handlers import auto_shelf_bid_control_menu as handler
from app.client_bot.user_interface.views import callbacks
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager import (
    AutoShelfBidControlTelegramError,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    OptimizationMetric,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)

pytestmark = pytest.mark.unit


@dataclass
class FakeMessage:
    """Message double for handlers that narrow via ``isinstance(..., Message)``.

    Production ``_tg_message`` uses the ``Message`` symbol imported in the
    handler module. Autouse fixture below patches that symbol to this class
    so unit doubles pass the same narrow without constructing aiogram models.
    """

    text: str
    answers: list[str] = field(default_factory=list)
    edit_text: AsyncMock = field(default_factory=AsyncMock)
    chat: SimpleNamespace = field(default_factory=lambda: SimpleNamespace(id=1))

    async def answer(self, text: str, **_: object) -> None:
        self.answers.append(text)


@pytest.fixture(autouse=True)
def _patch_handler_message_for_isinstance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Align FakeMessage with handler ``isinstance(..., Message)`` narrowing."""
    monkeypatch.setattr(handler, "Message", FakeMessage)


@dataclass
class FakeState:
    data: dict[str, object]
    cleared: bool = False
    state: object | None = None

    async def get_data(self) -> dict[str, object]:
        return self.data

    async def update_data(self, **kwargs: object) -> None:
        self.data.update(kwargs)

    async def set_state(self, state: object) -> None:
        self.state = state

    async def clear(self) -> None:
        self.cleared = True


def _view() -> AutoShelfBidControlViewDTO:
    return AutoShelfBidControlViewDTO(
        nmid=111,
        auto_adv_id=12345,
        enabled=True,
        has_settings=True,
        has_state=True,
        dry_run=True,
        bid_units_confirmed=False,
        actual_bid_minor=100,
        min_bid_minor=100,
        max_bid_minor=500,
        current_main_bid_minor=450,
        current_test_bid_minor=300,
        cycle_best_bid_minor=450,
        global_best_bid_minor=450,
        next_test_bid_minor=200,
        currency="RUB",
        current_mode="test",
        current_cycle_started_at=None,
        test_started_at=None,
        main_started_at=None,
        test_share=0.1,
        target_test_impressions=500,
        target_test_observation_minutes=60,
        target_main_impressions=4500,
        target_main_observation_minutes=540,
        min_bid_distance_minor=10,
        test_impressions=0,
        main_impressions=0,
        test_elapsed_minutes=0,
        main_elapsed_minutes=0,
        covered_points_count=0,
        bid_points_total=0,
        bid_points=[],
        cycle_covered_points_count=0,
        cycle_bid_points=[],
        last_reason=None,
        warnings=[],
        optimization_metric=OptimizationMetric.CPC,
        fact_cpo=None,
        resolve_cpo=None,
        auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.PLAN_DISTANCE,
    )


@pytest.mark.asyncio
async def test_send_main_screen_applies_refresh_before_build_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    service = type("FakeService", (), {})()
    service.apply_main_bid_refresh_if_needed = AsyncMock(
        side_effect=lambda *_args, **_kwargs: calls.append("apply")
    )
    service.build_view = AsyncMock(
        side_effect=lambda *_args, **_kwargs: (
            calls.append("build"),
            _view(),
        )[1]
    )
    callback_message = FakeMessage(text="main")
    callback_message.answer = AsyncMock(
        side_effect=lambda text, **_: calls.append(f"answer:{text}")
    )
    callback = SimpleNamespace(message=callback_message)
    monkeypatch.setattr(
        handler,
        "render_auto_shelf_bid_control_message",
        lambda *_: "rendered",
    )
    monkeypatch.setattr(
        handler,
        "build_auto_shelf_bid_control_keyboard",
        lambda *_: object(),
    )

    await handler._send_main_screen(
        callback,
        service=service,  # pyright: ignore[reportArgumentType]
        adv_setting_original_id=1,
    )

    assert calls[0] == "apply"
    assert calls[1] == "build"
    assert calls[2] == "answer:rendered"


@pytest.mark.asyncio
async def test_fsm_success_clears_state(monkeypatch: pytest.MonkeyPatch) -> None:
    message = FakeMessage(text="150")
    state = FakeState(data={"adv_setting_original_id": 1})
    fake_service = type(
        "FakeService",
        (),
        {
            "update_max_bid": AsyncMock(return_value=_view()),
            "build_view": AsyncMock(return_value=_view()),
        },
    )
    monkeypatch.setattr(handler, "AutoShelfBidControlTelegramService", lambda **_: fake_service())
    monkeypatch.setattr(handler, "render_auto_shelf_bid_settings_message", lambda *_: "settings")
    monkeypatch.setattr(handler, "build_auto_shelf_bid_settings_keyboard", lambda *_: object())

    await handler._handle_fsm_update(
        message=message,  # pyright: ignore[reportArgumentType]
        state=state,  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
        update_method="update_max_bid",
    )

    assert state.cleared is True
    assert "Настройка сохранена." in message.answers


@pytest.mark.asyncio
async def test_fsm_error_keeps_state(monkeypatch: pytest.MonkeyPatch) -> None:
    message = FakeMessage(text="bad")
    state = FakeState(data={"adv_setting_original_id": 1})

    class FakeService:
        async def update_max_bid(self, *_: object) -> None:
            raise AutoShelfBidControlTelegramError("error")

        async def build_view(self, *_: object) -> AutoShelfBidControlViewDTO:
            return _view()

    monkeypatch.setattr(handler, "AutoShelfBidControlTelegramService", lambda **_: FakeService())

    await handler._handle_fsm_update(
        message=message,  # pyright: ignore[reportArgumentType]
        state=state,  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
        update_method="update_max_bid",
    )

    assert state.cleared is False
    assert "error" in message.answers[-1]


@pytest.mark.asyncio
async def test_bid_points_empty_sends_message_not_callback_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Без покрытий — текст в чат; callback.answer не трогаем (есть middleware)."""
    chat_message = FakeMessage(text="main")
    callback = AsyncMock()
    callback.message = chat_message
    callback.answer = AsyncMock()

    async def _no_points(*_: object, **__: object) -> bool:
        return False

    monkeypatch.setattr(handler, "_show_bid_point_viewer", _no_points)
    monkeypatch.setattr(
        handler,
        "AutoShelfBidControlTelegramService",
        lambda **_: object(),
    )

    await handler.auto_shelf_bid_control_bid_points_router(
        callback=callback,
        callback_data=callbacks.AutoShelfBidControlBidPoints(
            adv_setting_original_id=1,
            index=0,
        ),
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    callback.answer.assert_not_awaited()
    assert chat_message.answers == ["В покрытии ставок теста пока нет доступных строк."]


def test_auto_shelf_bid_settings_keyboard_callback_data_fits_telegram_limit() -> None:
    keyboard = handler.build_auto_shelf_bid_settings_keyboard(_view(), 1151721977)
    callback_data_values = [
        button.callback_data
        for row in keyboard.inline_keyboard
        for button in row
        if button.callback_data is not None
    ]
    assert callback_data_values
    assert all(len(value.encode()) <= 64 for value in callback_data_values)


def test_auto_shelf_bid_control_action_normalization_accepts_compact_and_legacy_codes() -> None:
    assert (
        callbacks.normalize_auto_shelf_bid_control_action("tto")
        == "set_target_test_observation_minutes"
    )
    assert (
        callbacks.normalize_auto_shelf_bid_control_action(
            "set_target_test_observation_minutes"
        )
        == "set_target_test_observation_minutes"
    )
    assert callbacks.normalize_auto_shelf_bid_control_action("sp") == "set_strategy_plan_distance"
    assert callbacks.normalize_auto_shelf_bid_control_action("sm") == "strategy_menu"


@pytest.mark.asyncio
async def test_send_strategy_screen_uses_strategy_renderer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = type("FakeService", (), {})()
    service.build_view = AsyncMock(return_value=_view())
    callback_message = FakeMessage(text="settings")
    callback_message.answer = AsyncMock()
    callback = SimpleNamespace(message=callback_message)
    monkeypatch.setattr(
        handler,
        "render_auto_shelf_bid_strategy_message",
        lambda *_: "strategy",
    )
    monkeypatch.setattr(
        handler,
        "build_auto_shelf_bid_strategy_keyboard",
        lambda *_: object(),
    )

    await handler._send_strategy_screen(
        callback,
        service=service,  # pyright: ignore[reportArgumentType]
        adv_setting_original_id=1,
    )

    callback_message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_strategy_switch_updates_strategy_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback_message = FakeMessage(text="strategy")
    callback = SimpleNamespace(
        message=callback_message,
        from_user=SimpleNamespace(id=1),
    )
    fake_state = AsyncMock()
    fake_service = type("FakeService", (), {})()
    fake_service.set_strategy = AsyncMock(return_value=_view())
    fake_service.build_view = AsyncMock(
        return_value=replace(
            _view(),
            auto_shelf_bid_control_strategy=AutoShelfBidControlStrategy.CTR,
        )
    )
    monkeypatch.setattr(
        handler,
        "AutoShelfBidControlTelegramService",
        lambda **_: fake_service,
    )
    monkeypatch.setattr(
        handler,
        "render_auto_shelf_bid_strategy_message",
        lambda *_: "strategy-updated",
    )
    monkeypatch.setattr(
        handler,
        "build_auto_shelf_bid_strategy_keyboard",
        lambda *_: object(),
    )

    await handler.auto_shelf_bid_control_menu_router(
        callback=callback,  # pyright: ignore[reportArgumentType]
        callback_data=callbacks.AutoShelfBidControlMenu(
            action="sc",
            adv_setting_original_id=1,
        ),
        state=fake_state,  # pyright: ignore[reportArgumentType]
        bot=AsyncMock(),  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    callback_message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_retest_interval_days_enters_waiting_fsm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Settings action rid → FSM waiting_for_retest_interval_days."""
    from app.client_bot.user_interface import states

    callback_message = FakeMessage(text="settings")
    callback = SimpleNamespace(
        message=callback_message,
        from_user=SimpleNamespace(id=1),
    )
    state = FakeState(data={})
    monkeypatch.setattr(
        handler,
        "AutoShelfBidControlTelegramService",
        lambda **_: object(),
    )

    await handler.auto_shelf_bid_control_menu_router(
        callback=callback,  # pyright: ignore[reportArgumentType]
        callback_data=callbacks.AutoShelfBidControlMenu(
            action="rid",
            adv_setting_original_id=42,
        ),
        state=state,  # pyright: ignore[reportArgumentType]
        bot=AsyncMock(),  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    assert state.data.get("adv_setting_original_id") == 42
    assert state.state == states.AutoShelfBidControlFSM.waiting_for_retest_interval_days
    assert any("перетест" in a.lower() for a in callback_message.answers)


@pytest.mark.asyncio
async def test_waiting_for_retest_interval_days_persists_via_update_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FSM handler routes to update_retest_interval_days and clears state."""
    message = FakeMessage(text="14")
    state = FakeState(data={"adv_setting_original_id": 7})
    update = AsyncMock(return_value=_view())
    fake_service = type(
        "FakeService",
        (),
        {
            "update_retest_interval_days": update,
            "build_view": AsyncMock(return_value=_view()),
        },
    )
    monkeypatch.setattr(
        handler, "AutoShelfBidControlTelegramService", lambda **_: fake_service()
    )
    monkeypatch.setattr(
        handler, "render_auto_shelf_bid_settings_message", lambda *_: "settings"
    )
    monkeypatch.setattr(
        handler, "build_auto_shelf_bid_settings_keyboard", lambda *_: object()
    )

    await handler.auto_shelf_waiting_for_retest_interval_days(
        message=message,  # pyright: ignore[reportArgumentType]
        state=state,  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    update.assert_awaited_once_with(7, "14")
    assert state.cleared is True
    assert "Настройка сохранена." in message.answers


@pytest.mark.asyncio
async def test_asb_exh_reset_clears_pause_when_block_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """asb_exh_reset:<id> clears PG block and confirms without forced Auto start."""
    callback_message = FakeMessage(text="")
    callback = SimpleNamespace(data="asb_exh_reset:99", message=callback_message)
    clear = AsyncMock(return_value=True)
    fake_service = type(
        "FakeService",
        (),
        {"clear_shelf_exhausted_pause": clear},
    )
    monkeypatch.setattr(
        handler, "AutoShelfBidControlTelegramService", lambda **_: fake_service()
    )

    await handler.auto_shelf_exhausted_reset_pause(
        callback=callback,  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    clear.assert_awaited_once_with(99)
    assert any("Снят только блок паузы" in a for a in callback_message.answers)


@pytest.mark.asyncio
async def test_asb_exh_reset_reports_when_no_active_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback_message = FakeMessage(text="")
    callback = SimpleNamespace(data="asb_exh_reset:5", message=callback_message)
    clear = AsyncMock(return_value=False)
    fake_service = type(
        "FakeService",
        (),
        {"clear_shelf_exhausted_pause": clear},
    )
    monkeypatch.setattr(
        handler, "AutoShelfBidControlTelegramService", lambda **_: fake_service()
    )

    await handler.auto_shelf_exhausted_reset_pause(
        callback=callback,  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    clear.assert_awaited_once_with(5)
    assert any("не найдено" in a.lower() for a in callback_message.answers)


@pytest.mark.asyncio
async def test_asb_exh_reset_rejects_malformed_callback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    callback_message = FakeMessage(text="")
    callback = SimpleNamespace(data="asb_exh_reset:not-an-id", message=callback_message)
    clear = AsyncMock()
    monkeypatch.setattr(
        handler,
        "AutoShelfBidControlTelegramService",
        lambda **_: type("S", (), {"clear_shelf_exhausted_pause": clear})(),
    )

    await handler.auto_shelf_exhausted_reset_pause(
        callback=callback,  # pyright: ignore[reportArgumentType]
        redis_client=object(),  # pyright: ignore[reportArgumentType]
    )

    clear.assert_not_awaited()
    assert any("Некорректная" in a for a in callback_message.answers)
