from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest

from app.modules.v3_calibration_step_setting import telegram_handler as handler


@dataclass
class FakeMessage:
    text: str | None
    answers: list[str] = field(default_factory=list)

    async def answer(self, text: str, **_: object) -> None:
        self.answers.append(text)


@dataclass
class FakeState:
    data: dict[str, object]
    set_state_calls: list[object] = field(default_factory=list)
    updated_data: list[dict[str, object]] = field(default_factory=list)

    async def get_data(self) -> dict[str, object]:
        return self.data

    async def update_data(self, payload: dict[str, object]) -> None:
        self.updated_data.append(payload)

    async def set_state(self, value: object) -> None:
        self.set_state_calls.append(value)


@dataclass
class FakeCallbackMessage:
    answers: list[str] = field(default_factory=list)

    async def answer(self, text: str, **_: object) -> None:
        self.answers.append(text)


@dataclass
class FakeCallback:
    message: FakeCallbackMessage | None = None


class _FakeSessionCtx:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_v3_calibration_prompt_mentions_zero_to_fifty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adv = type("Adv", (), {"id": 1, "bot_active": True})()
    result = type("Result", (), {"scalar_one_or_none": lambda self: adv})()
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    monkeypatch.setattr(handler, "sm", lambda **_: _FakeSessionCtx(session))

    callback = FakeCallback(message=FakeCallbackMessage())
    state = FakeState(data={})
    await handler.change_v3_calibration_step(
        callback=callback,  # pyright: ignore[reportArgumentType]
        callback_data=type("CallbackData", (), {"adv_setting_original_id": 1})(),
        state=state,  # pyright: ignore[reportArgumentType]
    )

    assert callback.message is not None
    assert callback.message.answers
    assert "от 0 до 50" in callback.message.answers[0]
    assert state.updated_data == [
        {handler.FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID: 1}
    ]


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("text", "expected_fragment"),
    [
        ("0", "0 — отключить калибратор"),
        ("1", "Макс. шаг калибратора V3 изменён на 1"),
        ("50", "Макс. шаг калибратора V3 изменён на 50"),
        ("51", "Введите целое число от 0 до 50. 0 — отключить калибратор."),
        ("-1", "Введите целое число от 0 до 50"),
    ],
)
async def test_v3_calibration_step_validation_and_save(
    monkeypatch: pytest.MonkeyPatch,
    text: str,
    expected_fragment: str,
) -> None:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    monkeypatch.setattr(handler, "sm", lambda **kwargs: _FakeSessionCtx(session))

    message = FakeMessage(text=text)
    state = FakeState(
        data={handler.FSM_V3_CALIBRATION_STEP_ADV_SETTING_ID: 123},
    )

    await handler.set_v3_calibration_step(
        message=message,  # pyright: ignore[reportArgumentType]
        state=state,  # pyright: ignore[reportArgumentType]
        bot=AsyncMock(),  # pyright: ignore[reportArgumentType]
    )

    assert message.answers
    assert expected_fragment in message.answers[-1]
    if text in {"0", "1", "50"}:
        session.execute.assert_awaited_once()
        session.commit.assert_awaited_once()
        assert state.set_state_calls == [None]
    else:
        session.execute.assert_not_awaited()
        session.commit.assert_not_awaited()
        assert state.set_state_calls == []

