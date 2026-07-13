"""Telegram callbacks для экрана A/B Hold (spec ``card-ab-hold-mode``)."""

from aiogram.filters.callback_data import CallbackData


class CardAbHoldMenu(CallbackData, prefix="card_ab_hold_menu"):
    """Открыть экран инструкции A/B Hold."""

    adv_setting_original_id: int


class CardAbHoldEnable(CallbackData, prefix="card_ab_hold_enable"):
    """Включить ENTER (PENDING_SETUP)."""

    adv_setting_original_id: int


class CardAbHoldDisable(CallbackData, prefix="card_ab_hold_disable"):
    """Выключить режим (EXIT → OFF)."""

    adv_setting_original_id: int


class CardAbHoldBack(CallbackData, prefix="card_ab_hold_back"):
    """Назад к меню РК."""

    adv_setting_original_id: int
