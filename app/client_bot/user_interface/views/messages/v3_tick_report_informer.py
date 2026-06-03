"""Форматирование отчёта последнего V3-тика для Telegram UI."""

from __future__ import annotations

from app.client_bot.user_interface.views.messages.last_v3_action_informer import (
    format_snapshot_time_msk,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3PhaseStats,
    V3TickReportSnapshot,
)

_TELEGRAM_MAX_LEN = 4096

_SKIP_REASON_RU: dict[str, str] = {
    "resolve_invalid": "resolve недоступен",
    "shelf_inactive": "полка неактивна",
    "fact_le_max": "fact ≤ max",
    "guard_applied": "guard уже применён",
    "plan_fact_unchanged": "plan/fact не изменились",
    "views_unchanged": "views не изменились",
    "plan_fact_unchanged_and_views_unchanged": "plan/fact и views не изменились",
    "fact_gt_max": "fact > max",
}


def _skip_reason_display(code: str | None) -> str:
    if not code:
        return "пропуск"
    return _SKIP_REASON_RU.get(code, code)


def _phase_has_planned_actions(phase: V3PhaseStats) -> bool:
    return (phase.up + phase.down + phase.force_off + phase.rebalance) > 0


def _format_phase_line(phase: V3PhaseStats) -> list[str]:
    """Строки одного блока стадии."""
    title = phase.title_ru
    if phase.phase_id == "resolve_calibration":
        direct = phase.extra.get("calibration_direct")
        if direct:
            title = f"{title} · {str(direct).upper()}"
    lines = [f"▸ {title}"]
    if phase.phase_id == "filter":
        total = phase.extra.get("total", 0)
        operable = phase.extra.get("operable", 0)
        lines.append(f"  Управляемых: {operable} из {total}")
        return lines
    if phase.phase_id == "hard_status_sync":
        lines.append(f"  Синхронизировано: {phase.sync}")
        if phase.sync == 0 and phase.outcome_note:
            lines.append(f"  без изменений — {phase.outcome_note}")
        return lines
    if not phase.executed and phase.skip_reason:
        lines.append(f"  пропуск — {_skip_reason_display(phase.skip_reason)}")
        return lines
    if phase.executed and not _phase_has_planned_actions(phase):
        note = phase.outcome_note or "причина не зафиксирована"
        lines.append(f"  без изменений — {note}")
    else:
        parts = [f"↑{phase.up}", f"↓{phase.down}", f"off{phase.force_off}"]
        if phase.rebalance:
            parts.append(f"reb{phase.rebalance}")
        lines.append(f"  {'  '.join(parts)}")
    if phase.phase_id == "resolve_calibration" and phase.executed:
        steps = phase.extra.get("effective_steps")
        if steps is not None:
            lines.append(f"  шагов: {steps} (adaptive)")
    return lines


def format_v3_tick_report_text(snapshot: V3TickReportSnapshot | None) -> str:
    """Текст сообщения отчёта; ``None`` → заглушка «нет данных»."""
    if snapshot is None:
        return (
            "📊 Последний тик V3\n\n"
            "Нет данных о последнем тике апдейтера.\n"
            "Отчёт появится после первого успешного прогона V3."
        )
    header_name = snapshot.adv_name.strip() or f"adv_id={snapshot.adv_id}"
    lines: list[str] = [
        f"📊 Последний тик V3 · РК «{header_name}»",
        f"🕐 {format_snapshot_time_msk(snapshot.tick_at)} (МСК)",
        "",
    ]
    mode_line = f"Режим: {snapshot.campaign_mode}"
    if snapshot.sales_state:
        mode_line += f" · {snapshot.sales_state}"
    lines.append(mode_line)
    if snapshot.fact_cpa is not None:
        cpa_parts = [f"fact CPA: {snapshot.fact_cpa:.0f} ₽"]
        if snapshot.resolve is not None:
            cpa_parts.append(f"resolve: {snapshot.resolve:.0f} ₽")
        if snapshot.max_pay_for_order is not None:
            cpa_parts.append(f"max: {snapshot.max_pay_for_order:.0f} ₽")
        lines.append(" · ".join(cpa_parts))
    else:
        lines.append("fact CPA: н/д")
    lines.append(
        f"Ключей: {snapshot.total_keywords} всего → "
        f"{snapshot.operable_keywords} управляемых (hard_status 1|2)"
    )
    lines.append("")
    lines.append("────────────────────────")
    for phase in snapshot.phases:
        lines.extend(_format_phase_line(phase))
        lines.append("")
    lines.append("────────────────────────")
    lines.append("ИТОГ тика")
    delta = snapshot.aggression_delta
    sign = "+" if delta >= 0 else ""
    lines.append(
        f"  Изменение агрессии РК: {sign}{delta}  "
        f"({snapshot.aggression_score_before} → {snapshot.aggression_score_after})"
    )
    lines.append("  Баллы: MIN=1 · OPT=2 · MAX=3 · OFF=0")
    lines.append(
        f"  Применено: +{snapshot.net_up}↑  −{snapshot.net_down}↓  "
        f"off:{snapshot.net_force_off}"
    )
    if snapshot.hard_status_counts:
        lines.append("")
        lines.append("  Списки (hard_status):")
        for label, count in sorted(snapshot.hard_status_counts.items()):
            lines.append(f"  · {label}: {count}")
    text = "\n".join(lines)
    if len(text) > _TELEGRAM_MAX_LEN:
        return text[: _TELEGRAM_MAX_LEN - 20] + "\n\n… (обрезано)"
    return text
