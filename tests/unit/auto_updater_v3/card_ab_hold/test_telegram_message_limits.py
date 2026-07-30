"""Telegram payload limits для UI A/B Hold (openspec/policies/telegram_bot_api_limits.md).

Покрывает новые user-facing тексты и callback из diff vs stage:
handlers._INSTRUCTION / screen edit_text, answerCallbackQuery, inline keyboard,
меню-кнопка card_ab_hold_status_label, статус build_enter_poll_status_lines.

Класс: Telegram UI/message test. Регрессия — превышение лимитов TG Bot API
или утечка сырых `{placeholders}` до пользователя.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.enter_status import (
    build_enter_poll_status_lines,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.stats_enable_gate import (
    build_ab_hold_enable_blocked_by_stats_message,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.launch_validity_gate import (
    build_ab_hold_low_views_alert,
    build_ab_hold_low_views_warning_message,
    build_ab_hold_views_unavailable_alert,
    build_ab_hold_views_unavailable_message,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram import (
    handlers,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.telegram.callbacks import (
    CardAbHoldBack,
    CardAbHoldCancel,
    CardAbHoldDisable,
    CardAbHoldEnable,
    CardAbHoldLaunchAnyway,
    CardAbHoldMenu,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.ui_access import (
    card_ab_hold_status_label,
)
from app.client_bot import const

# Telegram Bot API limits (openspec/policies/telegram_bot_api_limits.md).
_TG_MESSAGE_TEXT_MAX = 4096
_TG_CALLBACK_ANSWER_MAX = 200
_TG_CALLBACK_DATA_BYTES_MAX = 64

# Worst-case adv_setting.id (signed 32-bit), realistic max для PG/int PK.
_WORST_CASE_ADV_SETTING_ID = 2_147_483_647

_CALLBACK_ANSWERS = (
    "Доступно только при включённом боте",
    "Подготовка A/B Hold…",
    "A/B Hold уже включён",
    "Идёт подготовка A/B Hold…",
    "Режим A/B выключен",
    "Включение отменено",
)

_CLOSED_SCREEN = (
    "Экран A/B Hold закрыт. Откройте меню рекламной кампании снова."
)

_REQUIRED_INSTRUCTION_PHRASES = (
    "прогрейте РК",
    "max CPO",
    "полки",
    "не меняйте цену",
    "ENTER",
    "HOLD",
    "EXIT",
    "биддер",
    "набор рекламных фраз зафиксирован",
    "отключите A/B Hold",
    "Статистика иногда временно недоступна",
    "не меняет состав ключей",
)


def _render_menu_screen(mode: CardAbHoldMode) -> str:
    """Собрать текст экрана как ``open_card_ab_hold_menu`` (worst-case mode)."""
    return f"{handlers._INSTRUCTION}\nСтатус: {mode.value}"


def _render_enter_screen(
    *,
    mode: CardAbHoldMode,
    abort_safe: bool | None,
    abort_can_continue: bool | None,
) -> str:
    """Собрать текст экрана как ``enable_card_ab_hold`` после poll LastAbort."""
    status = build_enter_poll_status_lines(
        mode=mode,
        abort_safe=abort_safe,
        abort_can_continue=abort_can_continue,
    )
    return f"{handlers._INSTRUCTION}\n{status}"


def _assert_no_raw_placeholders(text: str) -> None:
    """Сырые `{…}` шаблоны не должны доходить до пользователя."""
    assert "{" not in text
    assert "}" not in text


@pytest.mark.unit
@pytest.mark.parametrize("mode", list(CardAbHoldMode))
def test_ab_hold_menu_screen_text_within_telegram_limit(
    mode: CardAbHoldMode,
) -> None:
    """edit_text экрана меню ≤ 4096; ключевые фразы инструкции сохранены."""
    text = _render_menu_screen(mode)
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    _assert_no_raw_placeholders(text)
    for phrase in _REQUIRED_INSTRUCTION_PHRASES:
        assert phrase in text
    assert mode.value in text


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "abort_safe", "abort_can_continue"),
    [
        (CardAbHoldMode.PENDING_SETUP, None, None),
        (CardAbHoldMode.PENDING_SETUP, True, True),
        (CardAbHoldMode.PENDING_SETUP, False, False),
        (CardAbHoldMode.ACTIVE, None, None),
        (CardAbHoldMode.ACTIVE, True, True),
        (CardAbHoldMode.OFF, None, None),
        (CardAbHoldMode.OFF, True, True),
    ],
)
def test_ab_hold_enter_poll_screen_text_within_telegram_limit(
    mode: CardAbHoldMode,
    abort_safe: bool | None,
    abort_can_continue: bool | None,
) -> None:
    """Worst-case комбинации статуса ENTER ≤ 4096 символов."""
    text = _render_enter_screen(
        mode=mode,
        abort_safe=abort_safe,
        abort_can_continue=abort_can_continue,
    )
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    _assert_no_raw_placeholders(text)
    assert "Статус:" in text


@pytest.mark.unit
def test_ab_hold_disable_and_closed_screen_within_telegram_limit() -> None:
    """EXIT-экран и закрытие ≤ 4096."""
    disable_text = f"{handlers._INSTRUCTION}\nСтатус: off"
    assert len(disable_text) <= _TG_MESSAGE_TEXT_MAX
    _assert_no_raw_placeholders(disable_text)
    assert len(_CLOSED_SCREEN) <= _TG_MESSAGE_TEXT_MAX
    _assert_no_raw_placeholders(_CLOSED_SCREEN)


@pytest.mark.unit
@pytest.mark.parametrize("answer", _CALLBACK_ANSWERS)
def test_ab_hold_callback_answers_within_telegram_limit(answer: str) -> None:
    """answerCallbackQuery.text ≤ 200 (кириллица / ellipsis)."""
    assert len(answer) <= _TG_CALLBACK_ANSWER_MAX
    _assert_no_raw_placeholders(answer)


@pytest.mark.unit
def test_ab_hold_screen_keyboard_shape_and_callback_data_bytes() -> None:
    """Клавиатура OFF: 3 кнопки; callback_data ≤ 64 байт на worst-case adv_id.

    Decision §11: полная клавиатура (Enable+Disable+Back) — только при ``OFF``;
    это worst-case для проверки лимита callback_data всех трёх callback-типов.
    """
    kb = handlers._screen_keyboard(
        _WORST_CASE_ADV_SETTING_ID, CardAbHoldMode.OFF
    )
    rows = kb.inline_keyboard
    assert len(rows) == 3
    assert [btn.text for row in rows for btn in row] == [
        "Включить режим A/B",
        "Выключить режим A/B",
        "← Назад",
    ]
    expected_packs = [
        CardAbHoldEnable(
            adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID
        ).pack(),
        CardAbHoldDisable(
            adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID
        ).pack(),
        CardAbHoldBack(
            adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID
        ).pack(),
    ]
    actual_packs = [btn.callback_data for row in rows for btn in row]
    assert actual_packs == expected_packs
    for packed in actual_packs:
        assert packed is not None
        assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX


@pytest.mark.unit
def test_ab_hold_menu_entry_callback_data_bytes_worst_case_adv_id() -> None:
    """Кнопка меню РК: CardAbHoldMenu.pack() ≤ 64 байт при max id."""
    packed = CardAbHoldMenu(
        adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID
    ).pack()
    assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX


@pytest.mark.unit
@pytest.mark.parametrize(
    ("mode", "expected_label"),
    [
        (CardAbHoldMode.OFF, "A/B Hold: выкл"),
        (CardAbHoldMode.PENDING_SETUP, "A/B Hold: подготовка…"),
        (CardAbHoldMode.ACTIVE, "A/B Hold: ВКЛ"),
    ],
)
def test_ab_hold_menu_button_label_has_no_placeholders(
    mode: CardAbHoldMode,
    expected_label: str,
) -> None:
    """Текст кнопки входа в меню — без сырых placeholder и с ожидаемым label."""
    adv = SimpleNamespace(card_ab_hold_mode=mode.value, bot_active=True)
    label = card_ab_hold_status_label(adv)  # type: ignore[arg-type]
    assert label == expected_label
    _assert_no_raw_placeholders(label)


@pytest.mark.unit
def test_ab_hold_stats_blocked_message_within_telegram_limits() -> None:
    """7.2: blocked enable screen ≤4096 и содержит SUPPORT_LINK."""
    text = build_ab_hold_enable_blocked_by_stats_message(
        "full_adv_stat_update stale for adv_id=2147483647"
    )
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    assert const.SUPPORT_LINK in text
    _assert_no_raw_placeholders(text)
    screen = f"{handlers._INSTRUCTION}\n{text}"
    assert len(screen) <= _TG_MESSAGE_TEXT_MAX


@pytest.mark.unit
def test_ab_hold_low_views_warning_message_within_telegram_limits() -> None:
    """13.4: worst-case warning (§2c) ≤4096; без сырых placeholder."""
    text = build_ab_hold_low_views_warning_message(_WORST_CASE_ADV_SETTING_ID)
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    _assert_no_raw_placeholders(text)
    assert "max CPO" in text


@pytest.mark.unit
def test_ab_hold_low_views_alert_within_callback_answer_limit() -> None:
    """13.4: короткий alert (§2c) ≤200 символов."""
    alert = build_ab_hold_low_views_alert(_WORST_CASE_ADV_SETTING_ID)
    assert len(alert) <= _TG_CALLBACK_ANSWER_MAX
    _assert_no_raw_placeholders(alert)


@pytest.mark.unit
def test_ab_hold_views_unavailable_message_within_telegram_limits() -> None:
    """17.4: CH-error message (§2c) ≤4096; без сырых placeholder."""
    text = build_ab_hold_views_unavailable_message()
    assert len(text) <= _TG_MESSAGE_TEXT_MAX
    _assert_no_raw_placeholders(text)
    assert "временно недоступна" in text
    screen = f"{handlers._INSTRUCTION}\n{text}"
    assert len(screen) <= _TG_MESSAGE_TEXT_MAX


@pytest.mark.unit
def test_ab_hold_views_unavailable_alert_within_callback_answer_limit() -> None:
    """17.4: CH-error alert (§2c) ≤200 символов."""
    alert = build_ab_hold_views_unavailable_alert()
    assert len(alert) <= _TG_CALLBACK_ANSWER_MAX
    _assert_no_raw_placeholders(alert)


@pytest.mark.unit
def test_ab_hold_low_views_keyboard_callback_data_bytes() -> None:
    """13.4: launch-anyway / cancel callback_data ≤64 байт на worst-case adv id."""
    kb = handlers._low_views_warning_keyboard(_WORST_CASE_ADV_SETTING_ID)
    rows = kb.inline_keyboard
    assert [btn.text for row in rows for btn in row] == [
        "Всё равно запустить",
        "Отмена",
    ]
    expected_packs = [
        CardAbHoldLaunchAnyway(
            adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID
        ).pack(),
        CardAbHoldCancel(
            adv_setting_original_id=_WORST_CASE_ADV_SETTING_ID
        ).pack(),
    ]
    actual_packs = [btn.callback_data for row in rows for btn in row]
    assert actual_packs == expected_packs
    for packed in actual_packs:
        assert packed is not None
        assert 1 <= len(packed.encode("utf-8")) <= _TG_CALLBACK_DATA_BYTES_MAX
