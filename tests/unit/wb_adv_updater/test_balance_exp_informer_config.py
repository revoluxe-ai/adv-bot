"""Unit-тесты env-конфига Telegram-уведомлений updater."""

from __future__ import annotations

import pytest

from app.modules.wb_adv_updater.modules.balance_exp_informer.config import (
    balance_expiration_informer_enabled,
    updater_user_notifications_enabled,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),
        ("true", True),
        ("1", True),
        ("false", False),
        ("0", False),
        ("off", False),
    ],
)
def test_balance_expiration_informer_enabled(
    monkeypatch: pytest.MonkeyPatch,
    value: str | None,
    expected: bool,
) -> None:
    if value is None:
        monkeypatch.delenv("BALANCE_EXPIRATION_INFORMER_ENABLED", raising=False)
    else:
        monkeypatch.setenv("BALANCE_EXPIRATION_INFORMER_ENABLED", value)
    assert updater_user_notifications_enabled() is expected
    assert balance_expiration_informer_enabled() is expected
