"""Рендеринг текста и клавиатур Telegram для Auto Shelf Bid Control."""

from __future__ import annotations

from datetime import datetime

from app.client_bot.user_interface.views.callbacks import (
    AutoShelfBidControlBidPoints,
    AutoShelfBidControlMenu,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
    format_bid_minor_for_telegram,
    format_timestamp_for_telegram,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    BidPointStatsDTO,
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


def _format_ctr(ctr: float | None) -> str:
    """CTR как доля кликов к показам → проценты для Telegram."""
    if ctr is None:
        return "—"
    return f"{ctr * 100:.2f}%"


def _format_cycle_timestamp(value: datetime | str | None) -> str:
    """Дата/время цикла для Telegram без долей секунды."""
    return format_timestamp_for_telegram(value)


def _warnings_to_text(view: AutoShelfBidControlViewDTO) -> str:
    if not view.warnings:
        return "-"
    return "\n".join(f"- {item}" for item in view.warnings)


def _bid_point_cpc_sort_key(point: BidPointStatsDTO) -> tuple[float, int]:
    """Ключ сортировки: лучший CPC первым (``cart_cpa`` = CPC score в DTO)."""
    cpc = point.cart_cpa if point.cart_cpa is not None else float("inf")
    return (float(cpc), point.bid_minor)


def cycle_bid_coverage_icon(point: BidPointStatsDTO) -> str:
    """Значок статуса теста по ставке в текущем цикле."""
    if point.is_covered:
        return "✅"
    return "⏳"


def select_cycle_bid_points_for_viewer(
    points: list[BidPointStatsDTO],
) -> list[BidPointStatsDTO]:
    """Ставки цикла с показами для просмотрщика, от лучшего CPC к худшему.

    В списке все точки с ``impressions > 0``. ``is_covered`` — порог test показов
    достигнут (✅), иначе набор показов (⏳).
    """
    with_impressions = [p for p in points if p.impressions > 0]
    return sorted(with_impressions, key=_bid_point_cpc_sort_key)


def format_bid_point_line(point: BidPointStatsDTO) -> str:
    """Одна строка ставки цикла: статус, метрики, опционально лучшая точка."""
    status = cycle_bid_coverage_icon(point)
    best_mark = " ⭐" if point.is_best else ""
    cpc_text = _format_money(point.cart_cpa)
    return (
        f"{status}{best_mark} {format_bid(point.bid_minor, point.currency)}: "
        f"показы {point.impressions}, корзины {point.carts}, "
        f"клики {point.clicks}, CTR {_format_ctr(point.ctr)}, "
        f"расход {_format_money(point.spend)} ₽, CPC {cpc_text} ₽"
    )


def bid_point_viewer_page_count(
    total_points: int,
    page_size: int = TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
) -> int:
    """Число страниц просмотрщика покрытий (минимум 0)."""
    if total_points <= 0:
        return 0
    return (total_points + page_size - 1) // page_size


def clamp_bid_point_page(page: int, total_pages: int) -> int:
    """Безопасный номер страницы просмотрщика (0..total_pages-1)."""
    if total_pages <= 0:
        return 0
    if page < 0:
        return 0
    if page >= total_pages:
        return total_pages - 1
    return page


def slice_bid_points_page(
    points: list[BidPointStatsDTO],
    page: int,
    page_size: int = TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
) -> list[BidPointStatsDTO]:
    """Срез покрытых точек для страницы просмотрщика."""
    start = page * page_size
    return points[start : start + page_size]


BID_POINT_VIEWER_HEADER = "Ставки цикла (есть показы, сортировка по CPC):"
BID_POINT_VIEWER_LEGEND = (
    "✅ покрыта · ⏳ набор показов · ⭐ лучшая глобальная по CPC (есть клики)"
)


def render_bid_point_viewer_message(
    page: int,
    points: list[BidPointStatsDTO],
    page_size: int = TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
) -> str:
    """До ``page_size`` строк покрытий цикла на одной странице просмотрщика."""
    total = len(points)
    total_pages = bid_point_viewer_page_count(total, page_size)
    safe_page = clamp_bid_point_page(page, total_pages)
    chunk = slice_bid_points_page(points, safe_page, page_size)
    lines = [format_bid_point_line(point) for point in chunk]
    body = "\n".join(lines) if lines else "Нет ставок с показами в текущем цикле."
    return (
        f"{BID_POINT_VIEWER_HEADER}\n"
        f"{BID_POINT_VIEWER_LEGEND}\n\n"
        f"{body}\n\n"
        f"Страница {safe_page + 1} / {total_pages}"
    )


def build_bid_point_viewer_keyboard(
    adv_setting_original_id: int,
    page: int,
    total_points: int,
    page_size: int = TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
) -> InlineKeyboardMarkup:
    """Клавиатура просмотрщика: ◀️ / ▶️ по страницам, обновить, назад."""
    builder = InlineKeyboardBuilder()
    total_pages = bid_point_viewer_page_count(total_points, page_size)
    safe_page = clamp_bid_point_page(page, total_pages)
    nav_row: list[tuple[str, AutoShelfBidControlBidPoints]] = []
    if safe_page > 0:
        nav_row.append(
            (
                "◀️",
                AutoShelfBidControlBidPoints(
                    adv_setting_original_id=adv_setting_original_id,
                    index=safe_page - 1,
                ),
            )
        )
    if safe_page < total_pages - 1:
        nav_row.append(
            (
                "▶️",
                AutoShelfBidControlBidPoints(
                    adv_setting_original_id=adv_setting_original_id,
                    index=safe_page + 1,
                ),
            )
        )
    for text, callback_data in nav_row:
        builder.button(text=text, callback_data=callback_data.pack())
    builder.button(
        text="Обновить",
        callback_data=AutoShelfBidControlBidPoints(
            adv_setting_original_id=adv_setting_original_id,
            index=safe_page,
        ).pack(),
    )
    builder.button(
        text="К управлению",
        callback_data=AutoShelfBidControlMenu(
            action="open",
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    if nav_row:
        builder.adjust(len(nav_row), 1, 1)
    else:
        builder.adjust(1, 1)
    return builder.as_markup()


def render_auto_shelf_bid_control_message(view: AutoShelfBidControlViewDTO) -> str:
    """Собрать основной экран управления ставкой в полках."""
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
        f"Лучшая ставка цикла: {format_bid(view.cycle_best_bid_minor, view.currency)}\n"
        f"Лучшая глобальная ставка: {format_bid(view.global_best_bid_minor, view.currency)}\n"
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
        if view.has_state:
            builder.button(
                text="Покрытия цикла",
                callback_data=AutoShelfBidControlBidPoints(
                    adv_setting_original_id=adv_setting_original_id,
                    index=0,
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
