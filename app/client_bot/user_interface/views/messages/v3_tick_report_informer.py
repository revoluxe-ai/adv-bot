"""Форматирование отчёта последнего V3-тика для Telegram UI."""

from __future__ import annotations

from app.client_bot.const import TELEGRAM_TEXT_MESSAGE_LIMIT
from app.client_bot.user_interface.views.messages.last_v3_action_informer import (
    format_snapshot_time_msk,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    V3PhaseStats,
    V3TickReportSnapshot,
)

_CALIBRATION_BRANCH_RU: dict[str, str] = {
    "loosen": "UP",
    "tighten": "DOWN",
    "up": "UP",
    "down": "DOWN",
}


def _calibration_branch_ru(direct: str | None) -> str | None:
    """Отображение ветки калибровки: UP/DOWN (не loosen/tighten)."""
    if not direct:
        return None
    return _CALIBRATION_BRANCH_RU.get(str(direct).lower(), str(direct).upper())


def _format_calibration_step(
    applied: int | None,
    prev: int | None,
) -> str | None:
    """Строка adaptive-шагов калибровки для UI.

    ``applied`` — реально применённый шаг за тик; ``prev`` — предыдущий шаг из Redis.
    """
    if applied is None:
        return "нет"
    if prev is not None:
        return f"шаг {applied} (было {prev})"
    return f"шаг {applied}"


_SKIP_REASON_RU: dict[str, str] = {
    "resolve_invalid": "resolve недоступен",
    "shelf_inactive": "полка неактивна",
    "fact_le_max": "fact ≤ max",
    "guard_applied": "guard уже применён",
    "calibration_steps_disabled": "калибровка отключена",
    "configured_steps_gt_0": "configured max_step > 0, clamp пропущен",
    "plan_fact_unchanged": "plan/fact не изменились",
    "views_unchanged": "views не изменились",
    "plan_fact_unchanged_and_views_unchanged": "plan/fact и views не изменились",
    "fact_gt_max": "fact > max",
    "no_potential_up": "нет ступеней выше текущих (potential пуст)",
    "no_current_active": "нет active ключей для среза (все OFF)",
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
        branch = _calibration_branch_ru(phase.extra.get("calibration_direct"))
        if branch:
            title = f"{title} · {branch}"
        eff_raw = phase.extra.get("applied_steps")
        eff = int(eff_raw) if eff_raw is not None else None
        prev_raw = phase.extra.get("prev_effective_steps")
        prev = int(prev_raw) if prev_raw is not None else None
        step_text = _format_calibration_step(eff, prev)
        if step_text:
            title = f"{title} · {step_text}"
    lines = [f"▸ {title}"]
    if phase.phase_id == "filter":
        total = phase.extra.get("total", 0)
        operable = phase.extra.get("operable", 0)
        lines.append(f"  Управляемых: {operable} из {total}")
        return lines
    if phase.phase_id == "validate_state_by_hard_status":
        touched = phase.extra.get("hs1_touched", 0)
        if touched:
            lines.append(f"  ключей авто (hs=1): {touched}")
        elif phase.outcome_note:
            lines.append(f"  без изменений — {phase.outcome_note}")
        return lines
    if not phase.executed and phase.skip_reason:
        lines.append(f"  пропуск — {_skip_reason_display(phase.skip_reason)}")
        return lines
    if phase.executed and not _phase_has_planned_actions(phase):
        note = phase.outcome_note or "причина не зафиксирована"
        lines.append(f"  без изменений — {note}")
    else:
        display_down = phase.down + phase.force_off
        parts = [
            f"↑{phase.up}",
            f"on:{phase.ended_on}",
            f"↓{display_down}",
            f"off:{phase.ended_off}",
        ]
        if phase.rebalance:
            parts.append(f"reb{phase.rebalance}")
        lines.append(f"  {'  '.join(parts)}")
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
    cal_branch = _calibration_branch_ru(snapshot.calibration_direct)
    if cal_branch:
        cal_line = f"Калибровка: {cal_branch}"
        step_text = _format_calibration_step(
            snapshot.calibration_applied_steps,
            snapshot.calibration_prev_effective_steps,
        )
        if step_text:
            cal_line += f" · {step_text}"
        lines.append(cal_line)
    leader = snapshot.white_list_cost_leader
    if leader is not None:
        src = "state" if leader.cost_source == "state" else "PFO"
        tier = leader.data_tier or "—"
        line = (
            f"БС max ({src}, tier {tier}): «{leader.keyword_text}» "
            f"{leader.decision_cpo:.0f} ₽"
        )
        extras: list[str] = []
        if leader.state_cpo is not None:
            extras.append(f"state {leader.state_cpo:.0f} ₽")
        if leader.pfo_cpo is not None:
            extras.append(f"PFO {leader.pfo_cpo:.0f} ₽")
        if extras:
            line += f" ({', '.join(extras)})"
        if leader.strategy_mode:
            line += f" · {leader.strategy_mode}"
        lines.append(line)
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
        f"  Применено: +{snapshot.net_up}↑  on:{snapshot.net_on}  "
        f"−{snapshot.net_down}↓  off:{snapshot.net_force_off}"
    )
    if snapshot.hard_status_counts:
        lines.append("")
        lines.append("  Списки (hard_status):")
        for label, count in sorted(snapshot.hard_status_counts.items()):
            lines.append(f"  · {label}: {count}")
    text = "\n".join(lines)
    if len(text) > TELEGRAM_TEXT_MESSAGE_LIMIT:
        return text[: TELEGRAM_TEXT_MESSAGE_LIMIT - 20] + "\n\n… (обрезано)"
    return text
