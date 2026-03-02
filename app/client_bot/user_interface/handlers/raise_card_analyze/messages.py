"""Format raise card analyze result for Telegram."""

from __future__ import annotations

from typing import Any

from app.client_bot.const import ADMINS
from app.modules.raise_card_analyze.dto import (
    Confidence,
    DayPoint,
    KResult,
    TrendResult,
    WeekPoint,
)

# UI priority for weak_reasons (main reason to show)
WEAK_REASON_PRIORITY = ("low_spread", "flat_k", "wrong_sign", "low_corr")

# Русские подписи для уровня уверенности и источника k
CONFIDENCE_LEVEL_RU = {"high": "высокая", "medium": "средняя", "low": "низкая"}
K_SOURCE_RU = {"item": "товар", "adv": "кампания", "category": "категория", "global": "глобальный"}
# Уточнённые формулировки для отображения (история по чему считается «норма»)
K_SOURCE_DESC_RU = {
    "item": "эта карточка",
    "adv": "поисковая кампания, связанная с этой карточкой",
    "category": "категория товара на маркетплейсе",
    "global": "все кампании в базе",
}

INSTRUCTION = (
    "Как читать: индекс — показатель ранжирования «очищенный» от влияния ставки. "
    "Чем индекс ниже (больше в минус), тем лучше позиции при тех же деньгах. "
    "Сравниваем с предыдущим периодом: индекс упал → лучше 📉, вырос → хуже 📈.\n"
)

WRONG_SIGN_UI = (
    "Связь ставки и позиции инвертирована/не наблюдается. "
    "Проверь: смешение ключей/плейсментов/режимов, либо карточка в дебусте."
)


def _main_weak_reason(weak_reasons: tuple[str, ...]) -> str | None:
    for r in WEAK_REASON_PRIORITY:
        if r in weak_reasons:
            return r
    return None


def _weak_reason_ui_text(reason: str, k_result: KResult) -> str:
    if reason == "wrong_sign":
        return WRONG_SIGN_UI
    if reason == "low_spread":
        return "Мало вариации ставок за последние 14 дней. Создайте вариацию ставок, расширьте диапазон."
    if reason == "flat_k":
        return "Наклон k почти нулевой. Расширьте диапазон ставок или ключей."
    if reason == "low_corr":
        return "Слабая корреляция ставка–позиция. Включите другие ключи или увеличьте период."
    return "Нельзя оценить эффект ставки."


def format_raise_card_result(
    payload: dict[str, Any],
    adv_setting_id: int,
    view: str = "result",
    user_id: int | None = None,
) -> str:
    """Format full analysis payload as Telegram message text.
    view: 'result' | 'by_days' | 'by_weeks'
    user_id: если в ADMINS — показываем показы и строки; иначе скрываем.
    """
    is_admin = user_id is not None and user_id in ADMINS
    k_result: KResult = payload["k_result"]
    trend: TrendResult | None = payload.get("trend")
    confidence: Confidence = payload["confidence"]
    is_noisy_mode: bool = payload.get("is_noisy_mode", False)
    tail_share: float = payload.get("tail_share", 0.0)
    tail_mode: bool = payload.get("tail_mode", False)
    quality_gate_fail: bool = payload.get("quality_gate_fail", False)
    quality_gate_warn: bool = payload.get("quality_gate_warn", False)
    series = payload.get("series", [])
    series_type: str = payload.get("series_type", "day")

    lines: list[str] = []

    if view == "by_days":
        return _format_by_days(payload, is_admin=is_admin)
    if view == "by_weeks":
        return _format_by_weeks(payload, is_admin=is_admin)

    # (1) Недостаточно трафика
    if quality_gate_fail:
        lines.append("⚠️ Недостаточно трафика (показов за период < 100).")
        lines.append("Доберите трафик, затем повторите анализ.")
        _append_confidence_tail(lines, confidence, tail_mode, tail_share)
        return "\n".join(lines)

    # (2) Нельзя оценить эффект ставки (k_is_weak)
    if k_result.k_is_weak:
        lines.append("⚠️ Нельзя оценить эффект ставки.")
        main_r = _main_weak_reason(k_result.weak_reasons)
        if main_r:
            lines.append(_weak_reason_ui_text(main_r, k_result))
        if k_result.spread_used_recent is not None:
            lines.append(f"Вариация ставок (14 д): {k_result.spread_used_recent:.2f}")
        _append_confidence_tail(lines, confidence, tail_mode, tail_share)
        return "\n".join(lines)

    # trend=None: noisy or k_is_weak (we already handled k_is_weak above)
    if trend is None:
        if is_noisy_mode:
            lines.append("Режим шумный: min_d=1, вердикт не даём.")
        else:
            lines.append("Нет уверенного тренда.")
        if quality_gate_warn:
            lines.append("Мало точек за период.")
        _append_confidence_tail(lines, confidence, tail_mode, tail_share)
        return "\n".join(lines)

    # Verdict + change
    lines.append(f"Тренд: {trend.verdict.value}")
    lines.append(f"Изменение: {trend.change_pct:+.1f}%")
    if trend.last_median is not None and trend.prev_median is not None:
        lines.append(f"Медиана: было {trend.prev_median:.2f} → стало {trend.last_median:.2f}")
    if trend.mode:
        mode_label = "7д vs 7д" if trend.mode == "last_7_vs_prev_7" else "неделя к неделе"
        lines.append(f"(сравнение: {mode_label})")

    # Source k (краткое имя + уточнение, откуда история)
    k_src_ru = K_SOURCE_RU.get(k_result.k_source, k_result.k_source)
    k_desc = K_SOURCE_DESC_RU.get(k_result.k_source, k_result.k_source)
    lines.append(f"Источник k: {k_src_ru} ({k_desc})")
    if k_result.k_source != "item":
        lines.append("Оценка предварительная (k не по товару).")

    if k_result.spread_used_recent is not None:
        lines.append(f"Вариация ставок (14 д): {k_result.spread_used_recent:.2f}")

    _append_confidence_tail(lines, confidence, tail_mode, tail_share)

    # Table: cold = daily (last7/prev7 summary); optional short table
    if series_type == "day" and series:
        day_points: list[DayPoint] = series
        if len(day_points) >= 14:
            last7 = day_points[-7:]
            prev7 = day_points[-14:-7] if len(day_points) >= 14 else []
            med_last = _median_strength(last7)
            med_prev = _median_strength(prev7) if prev7 else 0.0
            lines.append("")
            lines.append("За 14 дней (последние 7 vs предыдущие 7):")
            lines.append(f"  последние 7 дней медиана индекса: {med_last:.2f}")
            if prev7:
                lines.append(f"  предыдущие 7 дней медиана индекса: {med_prev:.2f}")
    elif series_type == "week" and series:
        week_points: list[WeekPoint] = series
        if week_points:
            last_w = week_points[-1]
            lines.append("")
            tail = f", показов={last_w.sum_d:.0f}" if is_admin else ""
            lines.append(f"Последняя неделя: индекс {last_w.strength_index_med:.2f}{tail}")

    return "\n".join(lines)


def _median_strength(points: list[DayPoint]) -> float:
    if not points:
        return 0.0
    vals = [p.strength_index_med for p in points]
    vals.sort()
    n = len(vals)
    if n % 2 == 1:
        return vals[n // 2]
    return (vals[n // 2 - 1] + vals[n // 2]) / 2


def _append_confidence_tail(
    lines: list[str],
    confidence: Confidence,
    tail_mode: bool,
    tail_share: float,
) -> None:
    if tail_mode:
        lines.append(f"Доля хвоста: {tail_share * 100:.0f}%")
        lines.append("Позиции в хвосте, точность оценки ограничена клипом.")
    level_ru = CONFIDENCE_LEVEL_RU.get(confidence.level, confidence.level)
    lines.append(f"Уверенность: {level_ru} (оценка {confidence.score})")
    if confidence.notes:
        lines.append("Заметки: " + "; ".join(confidence.notes))


def _emoji_vs_prev(current: float, prev: float | None) -> str:
    """Эмодзи: индекс упал (ниже) = лучше 📉, вырос = хуже 📈."""
    if prev is None:
        return "➖"
    if current < prev:
        return "📉 лучше"
    if current > prev:
        return "📈 хуже"
    return "➖"


def _format_by_days(payload: dict[str, Any], is_admin: bool = False) -> str:
    """Формат: инструкция + таблица по дням с эмодзи лучше/хуже; итог внизу."""
    series = payload.get("series", [])
    series_type = payload.get("series_type", "day")

    lines: list[str] = [INSTRUCTION, "📅 Анализ по дням"]
    if series_type != "day" or not series:
        lines.append("Нет дневных данных.")
        return "\n".join(lines)
    day_points: list[DayPoint] = series
    prev_med: float | None = None
    for p in day_points[-14:]:
        em = _emoji_vs_prev(p.strength_index_med, prev_med)
        prev_med = p.strength_index_med
        part = f"  {em}  {p.day}  индекс {p.strength_index_med:.2f}"
        if is_admin:
            part += f"  показов={p.sum_d:.0f}"
        lines.append(part)
    if len(day_points) >= 14:
        last7 = day_points[-7:]
        prev7 = day_points[-14:-7]
        lines.append("")
        lines.append("Последние 7 дней: " + " ".join(f"{x.strength_index_med:.1f}" for x in last7))
        if prev7:
            lines.append("Предыдущие 7 дней: " + " ".join(f"{x.strength_index_med:.1f}" for x in prev7))
        med_last = _median_strength(last7)
        med_prev = _median_strength(prev7)
        diff = med_last - med_prev
        outcome = "лучше" if diff < 0 else ("хуже" if diff > 0 else "без изменений")
        emoji = "📉" if diff < 0 else ("📈" if diff > 0 else "➖")
        lines.append(f"{emoji} <b>Итог: {outcome}, разница {diff:+.2f}</b>")
    return "\n".join(lines)


def _format_by_weeks(payload: dict[str, Any], is_admin: bool = False) -> str:
    """Формат: инструкция + таблица по неделям с эмодзи лучше/хуже; итог внизу."""
    series = payload.get("series", [])
    series_type = payload.get("series_type", "day")
    lines: list[str] = [INSTRUCTION, "📅 Анализ по неделям"]
    if series_type != "week" or not series:
        lines.append("Нет данных по неделям (сейчас выбран режим по дням).")
        return "\n".join(lines)
    prev_med: float | None = None
    for p in series:
        em = _emoji_vs_prev(p.strength_index_med, prev_med)
        prev_med = p.strength_index_med
        part = f"  {em}  {p.week_start}  индекс {p.strength_index_med:.2f}"
        if is_admin:
            part += f"  показов={p.sum_d:.0f}  строк={p.rows_filtered}"
        lines.append(part)
    if len(series) >= 2:
        last_w = series[-1]
        prev_w = series[-2]
        diff = last_w.strength_index_med - prev_w.strength_index_med
        outcome = "лучше" if diff < 0 else ("хуже" if diff > 0 else "без изменений")
        emoji = "📉" if diff < 0 else ("📈" if diff > 0 else "➖")
        lines.append(f"{emoji} <b>Итог: {outcome}, разница {diff:+.2f}</b>")
    return "\n".join(lines)


