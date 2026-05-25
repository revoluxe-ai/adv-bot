"""Рендеринг текста и клавиатур Telegram для Auto Shelf Bid Control."""

from __future__ import annotations

from datetime import datetime

from app.client_bot.user_interface.views.callbacks import AutoShelfBidControlMenu
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    format_bid_minor_for_telegram,
    format_timestamp_for_telegram,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
)
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def format_bid(value: int | None, currency: str = "RUB") -> str:
    """Отформатировать ``bid_minor`` (копейки) в рубли для Telegram."""
    return format_bid_minor_for_telegram(value, currency)


def _format_money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"


def _format_cycle_timestamp(value: datetime | str | None) -> str:
    """Дата/время цикла для Telegram без долей секунды."""
    return format_timestamp_for_telegram(value)


def _warnings_to_text(view: AutoShelfBidControlViewDTO) -> str:
    if not view.warnings:
        return "-"
    return "\n".join(f"- {item}" for item in view.warnings)


def render_auto_shelf_bid_control_message(view: AutoShelfBidControlViewDTO) -> str:
    """Собрать основной экран управления ставкой в полках."""
    bid_lines: list[str] = []
    for point in view.bid_points[:15]:
        bid_lines.append(
            f"{format_bid(point.bid_minor, point.currency)}: показы {point.impressions}, "
            f"корзины {point.carts}, расход {_format_money(point.spend)} ₽, "
            f"CPA корзины {_format_money(point.cart_cpa)} ₽"
        )
    if not bid_lines:
        bid_lines.append("Статистики по тестовым ставкам пока недостаточно.")

    state_missing = (
        "Состояние управления ещё не создано. Оно будет создано на следующем цикле "
        "корутины после включения.\n"
        if not view.has_state
        else ""
    )
    dry_run_text = "включён" if view.dry_run else "выключен"
    gate_text = "подтверждён" if view.bid_units_confirmed else "не подтверждён"
    enabled_text = "включено" if view.enabled else "выключено"
    return (
        "⚙️ Управление ставкой в полках\n\n"
        f"Артикул: {view.nmid}\n"
        f"Auto РК: {view.auto_adv_id}\n"
        f"Статус управления: {enabled_text}\n"
        f"Dry-run (глобально): {dry_run_text}\n"
        f"Gate ставок: {gate_text}\n\n"
        f"{state_missing}"
        f"Режим сейчас: {view.current_mode or '—'}\n"
        f"Текущая ставка WB: {format_bid(view.actual_bid_minor, view.currency)}\n"
        f"Рабочая ставка main: {format_bid(view.current_main_bid_minor, view.currency)}\n"
        f"Тестовая ставка test: {format_bid(view.current_test_bid_minor, view.currency)}\n"
        f"Лучшая ставка цикла: {format_bid(view.best_bid_minor, view.currency)}\n"
        f"Следующая тестовая ставка: {format_bid(view.next_test_bid_minor, view.currency)}\n\n"
        "Диапазон теста:\n"
        f"Минимальная ставка WB: {format_bid(view.min_bid_minor, view.currency)}\n"
        f"Максимальная ставка: {format_bid(view.max_bid_minor, view.currency)}\n"
        f"Шаг между тестовыми ставками: {format_bid(view.min_bid_distance_minor, view.currency)}\n\n"
        "Прогресс:\n"
        f"Test: {view.test_impressions or 0} / {view.target_test_impressions or 0} показов\n"
        f"Main: {view.main_impressions or 0} / {view.target_main_impressions or 0} показов\n"
        f"Доля теста: {((view.test_share or 0) * 100):.2f}%\n\n"
        "Цикл:\n"
        f"Начат: {_format_cycle_timestamp(view.current_cycle_started_at)}\n"
        f"Тест начат: {_format_cycle_timestamp(view.test_started_at)}\n"
        f"Main начат: {_format_cycle_timestamp(view.main_started_at)}\n\n"
        "Покрытые ставки:\n"
        f"{chr(10).join(bid_lines)}\n\n"
        "Последнее событие:\n"
        f"{view.last_reason or '—'}\n\n"
        "Предупреждения:\n"
        f"{_warnings_to_text(view)}"
    )


def build_auto_shelf_bid_control_keyboard(
    view: AutoShelfBidControlViewDTO,
    adv_setting_original_id: int,
) -> InlineKeyboardMarkup:
    """Собрать inline-клавиатуру основного экрана управления."""
    builder = InlineKeyboardBuilder()
    if view.enabled:
        builder.button(
            text="Выключить управление",
            callback_data=AutoShelfBidControlMenu(
                action="disable",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Настройки",
            callback_data=AutoShelfBidControlMenu(
                action="settings",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Обновить",
            callback_data=AutoShelfBidControlMenu(
                action="refresh",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Сбросить цикл",
            callback_data=AutoShelfBidControlMenu(
                action="reset_cycle",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Вернуть main-ставку",
            callback_data=AutoShelfBidControlMenu(
                action="force_main",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
    else:
        builder.button(
            text="Включить управление",
            callback_data=AutoShelfBidControlMenu(
                action="enable",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Настройки",
            callback_data=AutoShelfBidControlMenu(
                action="settings",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Обновить",
            callback_data=AutoShelfBidControlMenu(
                action="refresh",
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
    builder.button(
        text="Назад",
        callback_data=AutoShelfBidControlMenu(
            action="back",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


def render_auto_shelf_bid_settings_message(view: AutoShelfBidControlViewDTO) -> str:
    """Собрать экран редактирования настроек управления."""
    enabled_text = "да" if view.enabled else "нет"
    dry_run_text = "включён" if view.dry_run else "выключен"
    return (
        "⚙️ Настройки управления ставкой в полках\n\n"
        f"Артикул: {view.nmid}\n\n"
        f"Максимальная ставка: {format_bid(view.max_bid_minor, view.currency)}\n"
        f"Доля теста: {((view.test_share or 0) * 100):.2f}%\n"
        f"Показов на тест: {view.target_test_impressions or '—'}\n"
        f"Шаг между тестовыми ставками: {format_bid(view.min_bid_distance_minor, view.currency)}\n"
        f"Dry-run (глобально, AUTO_SHELF_BID_CONTROL_DRY_RUN): {dry_run_text}\n\n"
        f"Управление включено: {enabled_text}"
    )


def build_auto_shelf_bid_settings_keyboard(adv_setting_original_id: int) -> InlineKeyboardMarkup:
    """Собрать inline-клавиатуру экрана настроек."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Изменить max ставку",
        callback_data=AutoShelfBidControlMenu(
            action="set_max_bid",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить долю теста",
        callback_data=AutoShelfBidControlMenu(
            action="set_test_share",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить показов на тест",
        callback_data=AutoShelfBidControlMenu(
            action="set_target_test_impressions",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить шаг между ставками",
        callback_data=AutoShelfBidControlMenu(
            action="set_min_bid_distance",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Назад к управлению ставкой",
        callback_data=AutoShelfBidControlMenu(
            action="open",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
