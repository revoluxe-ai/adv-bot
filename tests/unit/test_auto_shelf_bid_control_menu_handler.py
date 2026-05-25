from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from app.client_bot.user_interface.handlers import auto_shelf_bid_control_menu as handler
from app.client_bot.user_interface.views import callbacks
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager import (
    AutoShelfBidControlTelegramError,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
)

pytestmark = pytest.mark.unit


@dataclass
class FakeMessage:
    text: str
    answers: list[str] = field(default_factory=list)

    async def answer(self, text: str, **_: object) -> None:
        self.answers.append(text)


@dataclass
class FakeState:
    data: dict[str, object]
    cleared: bool = False

    async def get_data(self) -> dict[str, object]:
        return self.data

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
        target_main_impressions=4500,
        min_bid_distance_minor=10,
        test_impressions=0,
        main_impressions=0,
        covered_points_count=0,
        bid_points_total=0,
        bid_points=[],
        cycle_covered_points_count=0,
        cycle_bid_points=[],
        last_reason=None,
        warnings=[],
    )


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
    assert chat_message.answers == ["В текущем цикле пока нет покрытых ставок."]
