"""Рендеринг текста и клавиатур Telegram для Auto Shelf Bid Control."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence, TypeVar, cast

from app.client_bot.user_interface.views.callbacks import (
    AutoShelfBidControlBidPoints,
    AutoShelfBidControlMenu,
    compact_auto_shelf_bid_control_action,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.bid_units import (
    TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
    format_bid_minor_for_telegram,
    format_timestamp_for_telegram,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.dto import (
    AutoShelfBidControlViewDTO,
    BidPointStatsDTO,
    CoverageLayerBidDTO,
    OptimizationMetric,
)
from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import (
    AutoShelfBidControlStrategy,
)
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def format_bid(value: int | None, currency: str = "RUB") -> str:
    """Отформатировать ``bid_minor`` (копейки) в рубли для Telegram."""
    return format_bid_minor_for_telegram(value, currency)


def _format_money(value: float | None) -> str:
    if value is None:
        return "—"
    if value == float("inf"):
        return "∞"
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


def _as_dict(value: object) -> dict[str, object]:
    """Безопасно интерпретировать value как dict для read-only рендера."""
    if isinstance(value, dict):
        return cast(dict[str, object], value)
    return {}


def _coerce_float(value: object) -> float:
    """Преобразовать object в float для форматирования (без bool)."""
    if isinstance(value, bool):
        raise TypeError("bool is not a numeric bid metric")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"unsupported float source: {type(value)!r}")


def _format_rec_bid_int(value: object) -> str:
    if value is None:
        return "\u2014"
    try:
        if isinstance(value, bool):
            number = int(value)
        elif isinstance(value, int):
            number = value
        elif isinstance(value, float):
            number = int(round(value))
        elif isinstance(value, str):
            number = int(round(_coerce_float(value)))
        else:
            return "\u2014"
        return f"{number:,}".replace(",", " ")
    except (TypeError, ValueError):
        return "\u2014"


def _format_rec_bid_rub(value: object) -> str:
    if value is None:
        return "\u2014"
    try:
        amount = _coerce_float(value)
        if amount == float("inf"):
            return "\u221e \u20bd"
        return f"{amount:.2f} \u20bd"
    except (TypeError, ValueError):
        return "\u2014"


def _format_rec_bid_minor(value: object) -> str:
    if value is None:
        return "\u2014"
    try:
        if isinstance(value, bool):
            return "\u2014"
        if isinstance(value, int):
            minor = value
        elif isinstance(value, float):
            minor = int(round(value))
        elif isinstance(value, str):
            minor = int(round(_coerce_float(value)))
        else:
            return "\u2014"
        if minor <= 0 or minor % 100 != 0:
            return "\u2014"
        return f"{int(round(minor / 100))} \u20bd"
    except (TypeError, ValueError):
        return "\u2014"


def _format_rec_bid_number(value: object, *, precision: int) -> str:
    if value is None:
        return "\u2014"
    try:
        return f"{_coerce_float(value):.{precision}f}"
    except (TypeError, ValueError):
        return "\u2014"


def _format_plan_ranked_row(row: dict[str, object]) -> str:
    """Format Top-3 plan-ranked rows like coverage diagnostics."""
    parts: list[str] = []
    bid_value = row.get("bid")
    if bid_value is not None:
        parts.append(f"bid: {_format_rec_bid_minor(bid_value)}")
    impressions = row.get("impressions")
    if impressions is not None:
        parts.append(f"показы {_format_rec_bid_int(impressions)}")
    expected_daily_orders = row.get("expected_daily_orders")
    if expected_daily_orders is not None:
        parts.append(
            "прогноз заказов/сутки: "
            f"{_format_rec_bid_number(expected_daily_orders, precision=2)}"
        )
    cpo_value = row.get("cpo_rub")
    if cpo_value is None:
        cpo_value = row.get("expected_order_cost_rub")
    if cpo_value is not None:
        parts.append(f"CPO: {_format_rec_bid_rub(cpo_value)}")
    ctr_value = row.get("ctr")
    if ctr_value is not None:
        parts.append(f"CTR: {_format_ctr(_coerce_float(ctr_value))}")
    return " | ".join(parts) if parts else "-"


def _format_plan_ranked_rows(rows: object, *, limit: int = 3) -> str:
    """Format top-N plan-ranked rows with the same semantics as coverage rows."""
    if not isinstance(rows, list) or not rows:
        return "-"
    typed_rows = cast(list[object], rows)
    formatted_rows: list[str] = []
    for item in typed_rows[:limit]:
        formatted_rows.append(f"- {_format_plan_ranked_row(_as_dict(item))}")
    return "\n".join(formatted_rows) if formatted_rows else "-"



def _render_rec_bid_recommendation_block(view: AutoShelfBidControlViewDTO) -> str:
    """Build compact shelf bid recommendation block."""
    recommendation = view.rec_bid_recommendation
    if recommendation is None:
        return ""
    recommendation_dict = _as_dict(recommendation)
    plan_ranked = recommendation_dict.get("plan_ranked")
    plan_ranked_text = _format_plan_ranked_rows(plan_ranked)

    return (
        "\U0001f9ea \u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438 \u043f\u043e \u0441\u0442\u0430\u0432\u043a\u0435 \u043f\u043e\u043b\u043e\u043a\n"
        "\n"
        "Top-3 plan_ranked:\n"
        f"{plan_ranked_text}\n\n"
    )


def _format_coverage_layer_row(row: CoverageLayerBidDTO, currency: str) -> str:
    status = "✅" if not row.undercovered else "⏳"
    markers: list[str] = [status]
    if row.is_selected_next_test:
        markers.append("🎯")
    if row.is_best_plan or row.is_global_best:
        markers.append("⭐️")
    label_text = f" [{row.label}]" if row.label and row.label != "bid" else ""
    forecast_parts: list[str] = []
    if row.expected_daily_impressions is not None:
        forecast_parts.append(
            f"прогноз показов/сутки: {_format_rec_bid_int(row.expected_daily_impressions)}"
        )
    if row.expected_daily_clicks is not None:
        forecast_parts.append(
            f"прогноз кликов/сутки: {_format_rec_bid_int(row.expected_daily_clicks)}"
        )
    if row.expected_daily_orders is not None:
        forecast_parts.append(
            f"прогноз заказов/сутки: {_format_rec_bid_number(row.expected_daily_orders, precision=2)}"
        )
    if row.expected_order_cost_rub is not None:
        forecast_parts.append(f"CPO: {_format_rec_bid_rub(row.expected_order_cost_rub)}")
    if row.ctr is not None:
        forecast_parts.append(f"CTR: {_format_ctr(row.ctr)}")
    if row.plan_distance_score is not None:
        forecast_parts.append(
            f"score: {_format_rec_bid_number(row.plan_distance_score, precision=3)}"
        )
    if row.status_text is not None:
        forecast_parts.append(f"status: {row.status_text}")
    forecast_text = f" | {' | '.join(forecast_parts)}" if forecast_parts else ""
    return (
        f"{' '.join(markers)} {format_bid(row.bid_minor, currency)}{label_text}: "
        f"показы {row.impressions}, валидные часы {row.valid_hours}, "
        f"closed_layers {row.closed_layers}{forecast_text}"
    )


def _render_coverage_layer_block(view: AutoShelfBidControlViewDTO) -> str:
    return (
        "Покрытие ставок теста:\n"
        f"first_available_bucket_start: {_format_cycle_timestamp(view.coverage_first_available_bucket_start)}\n"
        f"current_layer: {view.coverage_current_layer if view.coverage_current_layer is not None else '—'}\n"
        f"undercovered_count: {view.coverage_undercovered_count if view.coverage_undercovered_count is not None else '—'}\n"
        f"selected_next_test_bid: {format_bid(view.coverage_selected_next_test_bid_minor, view.currency)}\n"
        "Подробный список: в пагинированном просмотрщике."
    )


def _bid_point_cpc_sort_key(point: BidPointStatsDTO) -> tuple[float, int]:
    """Ключ сортировки: лучший CPC первым (``cart_cpa`` = CPC score в DTO)."""
    cpc = point.cart_cpa if point.cart_cpa is not None else float("inf")
    return (float(cpc), point.bid_minor)


def _bid_point_ctr_sort_key(point: BidPointStatsDTO) -> tuple[float, int]:
    """Ключ сортировки: лучший CTR первым (по убыванию CTR)."""
    ctr = point.ctr if point.ctr is not None else float("-inf")
    # Отрицательный CTR для сортировки по убыванию
    return (-float(ctr), point.bid_minor)


def cycle_bid_coverage_icon(point: BidPointStatsDTO) -> str:
    """Значок статуса теста по ставке в текущем цикле."""
    if point.is_covered:
        return "✅"
    return "⏳"


def select_cycle_bid_points_for_viewer(
    points: list[BidPointStatsDTO],
    optimization_metric: OptimizationMetric = OptimizationMetric.CPC,
) -> list[BidPointStatsDTO]:
    """Ставки цикла с показами для просмотрщика.

    Сортировка зависит от метрики оптимизации:
    - CPC: от лучшего (меньший) к худшему (больший)
    - CTR: от лучшего (больший) к худшему (меньший)

    В списке все точки с ``impressions > 0``. ``is_covered`` — порог test показов
    достигнут (✅), иначе набор показов (⏳).
    """
    with_impressions = [p for p in points if p.impressions > 0]
    if optimization_metric == OptimizationMetric.CTR:
        return sorted(with_impressions, key=_bid_point_ctr_sort_key)
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


_TPoint = TypeVar("_TPoint")


def slice_bid_points_page(
    points: Sequence[_TPoint],
    page: int,
    page_size: int = TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
) -> list[_TPoint]:
    """Срез покрытых точек для страницы просмотрщика."""
    start = page * page_size
    return list(points[start : start + page_size])


def _bid_point_viewer_header(optimization_metric: OptimizationMetric) -> str:
    """Заголовок для страницы покрытия цикла в зависимости от метрики."""
    metric_name = "CTR" if optimization_metric == OptimizationMetric.CTR else "CPC"
    return f"Ставки цикла (есть показы, сортировка по {metric_name}):"


def _bid_point_viewer_legend(optimization_metric: OptimizationMetric) -> str:
    """Легенда для страницы покрытия цикла в зависимости от метрики."""
    if optimization_metric == OptimizationMetric.CTR:
        return "✅ покрыта · ⏳ набор показов · ⭐ лучшая глобальная по CTR"
    return "✅ покрыта · ⏳ набор показов · ⭐ лучшая глобальная по CPC (есть клики)"


# Legacy константы для обратной совместимости
BID_POINT_VIEWER_HEADER = "Покрытие ставок теста:"
BID_POINT_VIEWER_LEGEND = _bid_point_viewer_legend(OptimizationMetric.CPC)


def render_bid_point_viewer_message(
    page: int,
    points: list[CoverageLayerBidDTO],
    currency: str = "RUB",
    page_size: int = TELEGRAM_BID_POINTS_VIEWER_PAGE_SIZE,
    optimization_metric: OptimizationMetric = OptimizationMetric.CPC,
) -> str:
    """До ``page_size`` строк dense universe accumulated coverage на одной странице."""
    total = len(points)
    total_pages = bid_point_viewer_page_count(total, page_size)
    safe_page = clamp_bid_point_page(page, total_pages)
    chunk = slice_bid_points_page(points, safe_page, page_size)
    lines = [_format_coverage_layer_row(point, currency) for point in chunk]
    body = "\n".join(lines) if lines else "Нет ставок в dense universe."
    # Metric-aware builder kept for unit tests; page title stays legacy constant.
    _ = _bid_point_viewer_header(optimization_metric)
    header = "Покрытие ставок теста:"
    legend = (
        "✅ closed_layers > current_layer · "
        "⏳ closed_layers == current_layer · "
        "🎯 selected_next_test_bid · "
        "⭐️ best/global/best_plan"
    )
    return (
        f"{header}\n"
        f"{legend}\n\n"
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


def _format_main_waiting_reason(view: AutoShelfBidControlViewDTO) -> str:
    """Пояснить, сколько осталось до main observation gate."""
    elapsed = view.main_elapsed_minutes
    target = view.target_main_observation_minutes
    if elapsed is None or target is None:
        return view.last_reason or "—"
    if view.last_reason != "main_waiting_observation_time":
        return view.last_reason or "—"
    return (
        f"{view.last_reason}\n"
        f"Main observation: {elapsed} / {target} мин"
    )


def _format_last_event(view: AutoShelfBidControlViewDTO) -> str:
    """Последнее событие: при выключенном control не показываем active last_reason."""
    if view.primary_status == "disabled":
        return "disabled"
    return _format_main_waiting_reason(view)


def _format_strategy_label(strategy: AutoShelfBidControlStrategy) -> str:
    if strategy == AutoShelfBidControlStrategy.CTR:
        return "CTR"
    if strategy == AutoShelfBidControlStrategy.CPC:
        return "CPC"
    return "Best plan"


def _render_main_bid_line(view: AutoShelfBidControlViewDTO) -> str:
    """Лучшая свежая main-ставка (только из snapshot recommendation)."""
    main_bid = view.recommended_main_bid_minor
    if main_bid is None:
        main_bid = view.fresh_best_main_bid_minor
    if main_bid is None:
        explanation = view.main_target_explanation or "недостаточно протестированных ставок"
        return f"Лучшая ставка: — ({explanation})\n"
    if view.main_target_explanation:
        return (
            f"Лучшая ставка: {format_bid(main_bid, view.currency)} "
            f"({view.main_target_explanation})\n"
        )
    return f"Лучшая ставка: {format_bid(main_bid, view.currency)}\n"


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
    rec_bid_recommendation_text = _render_rec_bid_recommendation_block(view)
    coverage_layer_text = _render_coverage_layer_block(view)
    rec_bid_block = (
        f"\n\n{rec_bid_recommendation_text}" if rec_bid_recommendation_text else ""
    )
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
        + _render_main_bid_line(view)
        + f"Следующая тестовая ставка: {format_bid(view.fresh_next_test_bid_minor, view.currency)}\n\n"
        + "Диапазон теста:\n"
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
        f"{coverage_layer_text}\n\n"
        "Последнее событие:\n"
        f"{_format_last_event(view)}\n\n"
        "Предупреждения:\n"
        f"{_warnings_to_text(view)}"
        f"{rec_bid_block}"
    )





def render_auto_shelf_bid_strategy_message(view: AutoShelfBidControlViewDTO) -> str:
    """Собрать отдельный экран выбора режима main bid."""
    return (
        "⚙️ Режим main bid\n\n"
        f"Артикул: {view.nmid}\n"
        f"Текущий режим: {_format_strategy_label(view.auto_shelf_bid_control_strategy)}\n\n"
        "Доступные режимы:\n"
        "- Best plan\n"
        "- CTR\n"
        "- CPC"
    )



def build_auto_shelf_bid_strategy_keyboard(
    view: AutoShelfBidControlViewDTO,
    adv_setting_original_id: int,
) -> InlineKeyboardMarkup:
    """Собрать inline-клавиатуру отдельного экрана выбора режима main bid."""
    builder = InlineKeyboardBuilder()
    for strategy, action in (
        (AutoShelfBidControlStrategy.PLAN_DISTANCE, "set_strategy_plan_distance"),
        (AutoShelfBidControlStrategy.CTR, "set_strategy_ctr"),
        (AutoShelfBidControlStrategy.CPC, "set_strategy_cpc"),
    ):
        label = _format_strategy_label(strategy)
        if view.auto_shelf_bid_control_strategy == strategy:
            label = f"✅ {label}"
        builder.button(
            text=label,
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action(action),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
    builder.button(
        text="Назад к управлению ставкой",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("open"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


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
                action=compact_auto_shelf_bid_control_action("disable"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Настройки",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("settings"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text=f"Режим main bid: {_format_strategy_label(view.auto_shelf_bid_control_strategy)}",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("strategy_menu"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Обновить",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("refresh"),
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
                action=compact_auto_shelf_bid_control_action("reset_cycle"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Вернуть main-ставку",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("force_main"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
    else:
        builder.button(
            text="Включить управление",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("enable"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Настройки",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("settings"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text=f"Режим main bid: {_format_strategy_label(view.auto_shelf_bid_control_strategy)}",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("strategy_menu"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
        builder.button(
            text="Обновить",
            callback_data=AutoShelfBidControlMenu(
                action=compact_auto_shelf_bid_control_action("refresh"),
                adv_setting_original_id=adv_setting_original_id,
            ).pack(),
        )
    builder.button(
        text="Назад",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("back"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()


def render_auto_shelf_bid_settings_message(view: AutoShelfBidControlViewDTO) -> str:
    """Собрать экран редактирования настроек управления без выбора режима."""
    enabled_text = "да" if view.enabled else "нет"
    dry_run_text = "включён" if view.dry_run else "выключен"
    return (
        "⚙️ Настройки управления ставкой в полках\n\n"
        f"Артикул: {view.nmid}\n\n"
        f"Максимальная ставка: {format_bid(view.max_bid_minor, view.currency)}\n"
        f"Доля теста: {((view.test_share or 0) * 100):.2f}%\n"
        f"Показов на тест: {view.target_test_impressions or '—'}\n"
        f"Мин. минут теста: {view.target_test_observation_minutes or '—'}\n"
        f"Шаг между тестовыми ставками: {format_bid(view.min_bid_distance_minor, view.currency)}\n"
        f"Интервал перетеста (суток): {view.retest_interval_days}\n"
        f"Dry-run (глобально, AUTO_SHELF_BID_CONTROL_DRY_RUN): {dry_run_text}\n\n"
        f"Управление включено: {enabled_text}"
    )


def build_auto_shelf_bid_settings_keyboard(
    view: AutoShelfBidControlViewDTO,
    adv_setting_original_id: int,
) -> InlineKeyboardMarkup:
    """Собрать inline-клавиатуру экрана настроек без кнопки выбора режима."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Изменить max ставку",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("set_max_bid"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить долю теста",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("set_test_share"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить показов на тест",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("set_target_test_impressions"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить минут теста",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action(
                "set_target_test_observation_minutes"
            ),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить шаг между ставками",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("set_min_bid_distance"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Изменить интервал перетеста (сут)",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("set_retest_interval_days"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.button(
        text="Назад к управлению ставкой",
        callback_data=AutoShelfBidControlMenu(
            action=compact_auto_shelf_bid_control_action("open"),
            adv_setting_original_id=adv_setting_original_id,
        ).pack(),
    )
    builder.adjust(1)
    return builder.as_markup()
