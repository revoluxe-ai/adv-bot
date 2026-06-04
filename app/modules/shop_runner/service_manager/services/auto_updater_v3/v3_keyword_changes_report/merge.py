"""Мердж audit KeywordDTO в ``V3TickReportSnapshot`` для UI."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    title_ru_for_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3KeywordChangesSnapshot,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    PHASE_TITLES,
    V3PhaseStats,
    V3TickReportSnapshot,
)


def merge_keyword_changes_into_tick_snapshot(
    base: V3TickReportSnapshot,
    audit: V3KeywordChangesSnapshot,
) -> V3TickReportSnapshot:
    """Подменить счётчики фаз и net-итог из post-hoc audit; метаданные фаз сохранить.

    Args:
        base: Snapshot от ``V3TickReportCollector.build_snapshot``.
        audit: Post-hoc audit из ``KeywordDTO`` или NO_DATA builder.

    Returns:
        Новый snapshot с обновлёнными counters и aggression.
    """
    audit_by_phase = {item.phase_id: item for item in audit.by_phase}
    merged_phases: list[V3PhaseStats] = []
    seen_phase_ids: set[str] = set()

    for phase in base.phases:
        seen_phase_ids.add(phase.phase_id)
        breakdown = audit_by_phase.get(phase.phase_id)
        if breakdown is None:
            merged_phases.append(phase)
            continue
        merged_phases.append(
            phase.model_copy(
                update={
                    "planned": breakdown.planned,
                    "up": breakdown.up,
                    "down": breakdown.down,
                    "force_off": breakdown.force_off,
                    "rebalance": breakdown.rebalance,
                    "ended_off": breakdown.ended_off,
                    "ended_on": breakdown.ended_on,
                    "outcome_note": (
                        None
                        if breakdown.planned > 0
                        else phase.outcome_note
                    ),
                }
            )
        )

    for phase_id, breakdown in audit_by_phase.items():
        if phase_id in seen_phase_ids:
            continue
        meta = PHASE_TITLES.get(phase_id)
        possible = meta[1] if meta else ""
        merged_phases.append(
            V3PhaseStats(
                phase_id=phase_id,
                title_ru=breakdown.title_ru or title_ru_for_phase(phase_id),
                possible_actions_ru=possible,
                executed=True,
                planned=breakdown.planned,
                up=breakdown.up,
                down=breakdown.down,
                force_off=breakdown.force_off,
                rebalance=breakdown.rebalance,
                ended_off=breakdown.ended_off,
                ended_on=breakdown.ended_on,
            )
        )

    aggression_after = audit.aggression_score_after
    return base.model_copy(
        update={
            "phases": merged_phases,
            "net_up": audit.net_up,
            "net_down": audit.net_down,
            "net_force_off": audit.net_force_off,
            "net_on": audit.net_on,
            "aggression_score_after": aggression_after,
            "aggression_delta": aggression_after - base.aggression_score_before,
        }
    )
