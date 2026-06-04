"""Post-hoc audit для NO_DATA bootstrap из ``AppliedV3Action``."""

from __future__ import annotations

from datetime import datetime, timezone

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.applier import (
    AppliedV3Action,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.executor_phase_map import (
    title_ru_for_phase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_keyword_changes_report.models import (
    V3ExecutorPhaseBreakdown,
    V3KeywordChangeEntry,
    V3KeywordChangesSnapshot,
    V3KeywordStepRecord,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    mode_aggression_points,
)

_NO_DATA_PHASE_ID = "no_data_bootstrap"
_EXECUTOR_NAME = "DATA_BOOTSTRAP"


def build_from_applied_actions(
    applied: list[AppliedV3Action],
    *,
    adv_id: int,
    tick_at: datetime | None = None,
    keywords_aggression_modes: list[KeywordStrategyMode] | None = None,
) -> V3KeywordChangesSnapshot:
    """Собрать audit для NO_DATA из фактически применённых bootstrap-действий.

    Args:
        applied: Список ``ledger.applied_actions()`` после bootstrap.
        adv_id: ID рекламной кампании.
        tick_at: Время тика (UTC).
        keywords_aggression_modes: Режимы ключей для aggression_after; если
            ``None`` — не пересчитывается (0).

    Returns:
        Snapshot с одной фазой ``no_data_bootstrap``.
    """
    ts = tick_at or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    up = down = force_off = 0
    entries: list[V3KeywordChangeEntry] = []
    touched_ids: set[int] = set()
    keyword_modes: dict[int, tuple[KeywordStrategyMode, KeywordStrategyMode]] = {}

    for item in applied:
        ks_id = item.keyword_setting_id
        if ks_id is not None:
            touched_ids.add(int(ks_id))
        action_label = item.action.name
        if item.action == V3ActionType.UP:
            up += 1
        elif item.action == V3ActionType.DOWN:
            down += 1
        elif item.action == V3ActionType.FORCE_OFF:
            force_off += 1
        else:
            continue
        if ks_id is None:
            continue
        kid = int(ks_id)
        if kid not in keyword_modes:
            keyword_modes[kid] = (item.from_mode, item.from_mode)
        start, _ = keyword_modes[kid]
        keyword_modes[kid] = (start, item.to_mode)
        entries.append(
            V3KeywordChangeEntry(
                keyword_setting_id=int(ks_id),
                keyword_text=item.keyword_text,
                stored_mode=item.from_mode.name,
                current_mode=item.to_mode.name,
                mode_chain=f"{item.from_mode.name}→{item.to_mode.name}",
                executor_short_labels="boot",
                steps=[
                    V3KeywordStepRecord(
                        executor_name=_EXECUTOR_NAME,
                        from_mode=item.from_mode.name,
                        to_mode=item.to_mode.name,
                        action=action_label,
                    )
                ],
            )
        )

    ended_off = sum(1 for _, end in keyword_modes.values() if end == KeywordStrategyMode.OFF)
    ended_on = sum(
        1
        for start, end in keyword_modes.values()
        if start == KeywordStrategyMode.OFF and end != KeywordStrategyMode.OFF
    )
    net_on = ended_on

    breakdown = V3ExecutorPhaseBreakdown(
        phase_id=_NO_DATA_PHASE_ID,
        executor_name=_EXECUTOR_NAME,
        title_ru=title_ru_for_phase(_NO_DATA_PHASE_ID),
        planned=up + down + force_off,
        up=up,
        down=down,
        force_off=force_off,
        keywords_touched=len(touched_ids),
        ended_off=ended_off,
        ended_on=ended_on,
    )

    aggression_after = 0
    if keywords_aggression_modes is not None:
        aggression_after = sum(
            mode_aggression_points(mode) for mode in keywords_aggression_modes
        )

    return V3KeywordChangesSnapshot(
        tick_at=ts,
        adv_id=adv_id,
        source="applied_actions",
        changed_keywords=len(entries),
        net_up=up,
        net_down=down,
        net_force_off=force_off,
        net_on=net_on,
        aggression_score_after=aggression_after,
        by_phase=[breakdown],
        keyword_entries=sorted(entries, key=lambda e: e.keyword_text.lower()),
    )
