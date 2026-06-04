from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.client_bot.user_interface.handlers import (
    add_black_phrases,
    add_relevant_phrase_templates,
)
from app.client_bot.user_interface.views import callbacks


def _session_cm_with_adv(adv_obj: object) -> AsyncMock:
    session = AsyncMock()
    session.get = AsyncMock(return_value=adv_obj)
    cm = AsyncMock()
    cm.__aenter__.return_value = session
    cm.__aexit__.return_value = None
    return cm


@pytest.mark.asyncio
async def test_export_black_phrases_sends_document() -> None:
    callback = SimpleNamespace(from_user=SimpleNamespace(id=123))
    bot = SimpleNamespace(send_document=AsyncMock())
    callback_data = callbacks.ExportBlackPhrases(adv_setting_id=11)

    manager = AsyncMock()
    manager.get_relevant_template_data = AsyncMock(return_value=["one", "two"])

    with patch.object(
        add_black_phrases, "sm", return_value=_session_cm_with_adv(object())
    ), patch.object(add_black_phrases, "RelevantPhraseManager", return_value=manager):
        await add_black_phrases.export_black_phrases(callback, bot, callback_data)

    bot.send_document.assert_awaited_once()
    sent_document = bot.send_document.await_args.kwargs["document"]
    assert sent_document.filename == "black_phrases.txt"


@pytest.mark.asyncio
async def test_export_relevant_templates_sends_document() -> None:
    callback = SimpleNamespace(from_user=SimpleNamespace(id=123))
    bot = SimpleNamespace(send_document=AsyncMock())
    callback_data = callbacks.ExportRelevantPhraseTemplates(adv_setting_id=22)

    manager = AsyncMock()
    manager.get_relevant_phrases_template_data = AsyncMock(
        return_value=["alpha", "beta"]
    )

    with patch.object(
        add_relevant_phrase_templates, "sm", return_value=_session_cm_with_adv(object())
    ), patch.object(
        add_relevant_phrase_templates, "RelevantPhraseManager", return_value=manager
    ):
        await add_relevant_phrase_templates.export_relevant_phrase_templates(
            callback, bot, callback_data
        )

    bot.send_document.assert_awaited_once()
    sent_document = bot.send_document.await_args.kwargs["document"]
    assert sent_document.filename == "relevant_phrase_templates.txt"
