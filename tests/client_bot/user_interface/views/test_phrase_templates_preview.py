from unittest.mock import MagicMock

from app.client_bot.user_interface.views import messages


def test_waiting_for_black_phrases_truncates_and_shows_export_hint() -> None:
    view = messages.WaitingForBlackPhrases(bot=MagicMock(), chat_id=1)
    view.adv_setting_id = 10
    view.black_phrases = [f"phrase-{idx}-" + ("x" * 80) for idx in range(200)]

    text = view.text
    keyboard = view.keyboard

    assert len(text) <= 1400
    assert 'Чтобы получить весь список, нажмите кнопку "Выгрузить фразы"' in text
    texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert "Выгрузить фразы" in texts


def test_waiting_for_relevant_templates_short_text_without_hint() -> None:
    view = messages.WaitingForRelevantPhraseTemplates(bot=MagicMock(), chat_id=1)
    view.adv_setting_id = 20
    view.relevant_phrases = ["платье", "сарафан"]

    text = view.text
    keyboard = view.keyboard

    assert 'Чтобы получить весь список, нажмите кнопку "Выгрузить фразы"' not in text
    texts = [btn.text for row in keyboard.inline_keyboard for btn in row]
    assert "Выгрузить фразы" in texts
