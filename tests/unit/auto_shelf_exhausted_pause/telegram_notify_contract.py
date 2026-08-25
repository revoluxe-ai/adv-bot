"""ContractCase + recording fake for ASEP Telegram notify (S15).

Spec: ``Notify explains why and when`` — HTML text + ``parse_mode=HTML``
on ``NotificationSender.send_message``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

CONTRACT_ID = "asep.telegram.shelf_exhausted_notify.v1"

# Golden inputs for shared ContractCase / scenario_seam.
NOTIFY_CASE_SHOP_NAME = "Shop <X>"
NOTIFY_CASE_CAMPAIGN_NAME = "Camp & Co"
NOTIFY_CASE_RESOLVE_CPO_KIND = "max"
NOTIFY_CASE_RESOLVE_CPO_VALUE = 250.0
NOTIFY_CASE_DUE_AT = datetime(2026, 8, 20, 12, 0, 0, tzinfo=UTC)
NOTIFY_CASE_CHAT_ID = 424242
NOTIFY_CASE_ADV_SETTING_ID = 77


@dataclass(frozen=True)
class TelegramNotifyContractCase:
    """Ожидаемый send_message shape для shelf-exhausted paid notify."""

    case_id: str
    chat_id: int
    require_html_markup: bool
    require_parse_mode_html: bool
    disable_web_page_preview: bool


TELEGRAM_NOTIFY_CASES: tuple[TelegramNotifyContractCase, ...] = (
    TelegramNotifyContractCase(
        case_id="enter_notify_html_parse_mode",
        chat_id=NOTIFY_CASE_CHAT_ID,
        require_html_markup=True,
        require_parse_mode_html=True,
        disable_web_page_preview=True,
    ),
)


@dataclass
class RecordingTelegramNotificationSender:
    """Thin-end fake for ``NotificationSender.send_message`` kwargs shape."""

    calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = field(default_factory=list)

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> bool:
        """Как NotificationSender.send_message(chat_id, text, **kwargs)."""
        self.calls.append(((chat_id, text), kwargs))
        return True

    def assert_matches_case(
        self,
        case: TelegramNotifyContractCase,
        *,
        expected_text: str | None = None,
    ) -> None:
        """Проверка parity: HTML body + parse_mode=HTML + optional text match."""
        assert self.calls, f"{case.case_id}: expected send_message call"
        (chat_id, text), kwargs = self.calls[0]
        assert chat_id == case.chat_id
        if expected_text is not None:
            assert text == expected_text
        if case.require_html_markup:
            assert "<b>" in text
        if case.require_parse_mode_html:
            assert kwargs.get("parse_mode") == "HTML", (
                f"{case.case_id}: parse_mode must be HTML; kwargs={kwargs!r}"
            )
        if case.disable_web_page_preview:
            assert kwargs.get("disable_web_page_preview") is True
        assert kwargs.get("reply_markup") is not None
