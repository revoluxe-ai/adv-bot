"""RED: shop NRF reset must not claim A/B Hold skip when none skipped.

ROOT-001 / BUGCASE-NRF-UX-HOLD-SKIP-MSG: ``reset_shop_non_relevant_phrases``
always appends «Кампании в A/B Hold пропущены» to Telegram success copy.
Peer ``apply_defaults_for_shop`` mentions Hold only when ``skipped_ab_hold > 0``.

Invariant: Hold-skip claim only when skipped_count > 0.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.handlers.adv_setting.adv_setting import (
    reset_shop_non_relevant_phrases,
)
from app.client_bot.user_interface.views.callbacks import (
    ResetShopNonRelevantPhrases,
)

_HANDLER = "app.client_bot.user_interface.handlers.adv_setting.adv_setting"
_UTILS = "app.client_bot.user_interface.handlers.adv_setting.utils"
_HOLD_SKIP_CLAIM = "Кампании в A/B Hold пропущены"


class _MockSessionMaker:
    """Minimal async context manager standing in for ``sm``."""

    def __init__(self, session: object) -> None:
        self._session = session

    def __call__(self, read_only: bool = False) -> "_MockSessionMaker":
        return self

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def _callback(chat_id: int = 4242) -> SimpleNamespace:
    """Minimal CallbackQuery stub with ``message.chat.id``."""
    return SimpleNamespace(message=SimpleNamespace(chat=SimpleNamespace(id=chat_id)))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_shop_nrf_message_omits_hold_skip_when_none_skipped() -> None:
    """No held campaigns skipped → success copy must not claim A/B Hold skip.

    Production currently always appends the Hold-skip sentence even when
    ``update_keywords`` only returns an updated rowcount (no skip signal).
    After fix (peer apply_defaults): Hold-skip claim only if skipped_count > 0.
    """
    bot = AsyncMock()
    state = MagicMock()
    session = AsyncMock()
    shop_menu_instance = AsyncMock()
    updated_count = 3  # NRF rows reset; zero Hold skips in this scenario

    with (
        patch(f"{_HANDLER}.sm", _MockSessionMaker(session)),
        patch(
            f"{_HANDLER}.ShopMenu",
            MagicMock(return_value=shop_menu_instance),
        ),
        patch(
            f"{_UTILS}.update_keywords",
            AsyncMock(return_value=updated_count),
        ),
    ):
        await reset_shop_non_relevant_phrases(
            callback=_callback(chat_id=4242),  # type: ignore[arg-type]
            callback_data=ResetShopNonRelevantPhrases(
                wb_user_cabinet_original_id=77
            ),
            bot=bot,
            state=state,
        )

    bot.send_message.assert_awaited_once()
    send_text = bot.send_message.await_args.args[1]
    assert f"Сброшено НРФ: {updated_count}" in send_text
    assert _HOLD_SKIP_CLAIM not in send_text, (
        "UX false claim: success copy must not assert A/B Hold skips when "
        "skipped_count==0 (peer apply_defaults_for_shop is conditional)"
    )
    shop_menu_instance.assert_awaited_once()
