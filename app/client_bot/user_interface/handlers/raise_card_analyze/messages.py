"""Format raise card analyze result for Telegram."""

from __future__ import annotations

from typing import Any

from app.client_bot.const import ADMINS
from app.modules.raise_card_analyze.dto import DayPoint

INSTRUCTION = (
    "Как читать: индекс — показатель ранжирования «очищенный» от влияния ставки. "
    "Чем индекс ниже (больше в минус), тем лучше позиции при тех же деньгах. "
    "Сравниваем с предыдущим периодом: индекс упал → лучше 📉, вырос → хуже 📈.\n"
)


def format_raise_card_result(
    payload: dict[str, Any],
    adv_setting_id: int,
    view: str = "by_days",
    user_id: int | None = None,
) -> str:
    """Format full analysis payload as Telegram message text.
    view: 'by_days' | 'by_weeks'
    user_id: если в ADMINS — показываем показы и строки; иначе скрываем.
    """
    is_admin = user_id is not None and user_id in ADMINS
    if view == "by_weeks":
        return _format_by_weeks(payload, is_admin=is_admin)
    return _format_by_days(payload, is_admin=is_admin)


def _median_strength(points: list[DayPoint]) -> float:
    if not points:
        return 0.0
    vals = [p.strength_index_med for p in points]
    vals.sort()
    n = len(vals)
    if n % 2 == 1:
        return vals[n // 2]
    return (vals[n // 2 - 1] + vals[n // 2]) / 2


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


