"""Логика cooldown «выше цели при мин. ставке»: 24 ч заморозка, затем 1 ч ожидание + ≥1 показ, окно перетеста 25–26 ч."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.mp.wb.dto import AdvMinNmidsBids
from app.core.mp.wb.min_bid_defaults import default_min_bid_rub, resolve_search_min_bid_rub
from app.core.mp.wb.dto.adv_placement_type import AdvPlacementType
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.above_target_min_bid_diagnostic import (
    AboveTargetMinBidDiagnostic,
    AboveTargetMinBidDiagnosticState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.pre_calculated_keyword import (
    PreCalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)

_FREEZE_H = timedelta(hours=24)
_WAIT_AFTER_FREEZE_H = timedelta(hours=1)  # после 24 ч — ещё 1 ч до окна перетеста (всего 25 ч)
_RETEST_WINDOW_H = timedelta(hours=1)  # 25–26 ч: перетест при росте показов

# Redis TTL ≥ полного цикла, иначе ключ исчезает до конца окна 25–26 ч и цикл сбрасывается.
_ABOVE_TARGET_FULL_CYCLE = _FREEZE_H + _WAIT_AFTER_FREEZE_H + _RETEST_WINDOW_H
ABOVE_TARGET_MIN_BID_COOLDOWN_REDIS_TTL_SECONDS = int(
    _ABOVE_TARGET_FULL_CYCLE.total_seconds()
) + 3600  # +1 ч запас к границе следующего цикла

COOLDOWN_RETEST_DISPLAY_TAG = "Т"


def max_search_min_bid_for_complex_nmids(
    nmids: list[int], min_bids: AdvMinNmidsBids | None
) -> int | None:
    """Максимум мин. CPM поиска по артикулам комплекса.

    При пустом/невалидном кеше — ``settings.MIN_BID_SEARCH_DEFAULT`` (руб.).
    """
    if not nmids:
        return None
    if min_bids is None or not min_bids.search:
        return default_min_bid_rub(AdvPlacementType.SEARCH_ADV)
    values = [resolve_search_min_bid_rub(nmid, min_bids) for nmid in nmids]
    m = max(values)
    if m <= 0:
        return default_min_bid_rub(AdvPlacementType.SEARCH_ADV)
    return m


def current_position_for_rule(pre_kw: PreCalculatedKeyword) -> int:
    return max(round(pre_kw.cluster_stat.position), 1)


def is_above_target_at_min_bid(pre_kw: PreCalculatedKeyword, min_bid_for_adv: int) -> bool:
    target = pre_kw.keyword_setting.target_place
    if target is None:
        return False
    cpm = int(pre_kw.cpm)
    if cpm <= 0:
        return False
    pos = current_position_for_rule(pre_kw)
    return pos < target and cpm <= min_bid_for_adv


def _normalize_entry(
    val: datetime | AboveTargetCooldownEntry | None,
) -> AboveTargetCooldownEntry | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return AboveTargetCooldownEntry(val, 0)
    return val


@dataclass(frozen=True)
class _MsGateSnapshot:
    """Снимок pos/min_bid gates для diagnostic (mirror is_above_target_at_min_bid)."""

    current_position: int | None
    target_place: int | None
    position_condition_pass: bool | None
    current_cpm: int | None
    min_bid: int | None
    min_bid_condition_pass: bool | None


def _ms_gate_snapshot(
    pre_kw: PreCalculatedKeyword, min_bid_for_adv: int | None
) -> _MsGateSnapshot:
    target = pre_kw.keyword_setting.target_place
    pos = current_position_for_rule(pre_kw)
    cpm_raw = int(pre_kw.cpm) if pre_kw.cpm and int(pre_kw.cpm) > 0 else None
    position_pass: bool | None = None
    min_bid_pass: bool | None = None
    if target is not None:
        position_pass = pos < target
    if cpm_raw is not None and min_bid_for_adv is not None:
        min_bid_pass = cpm_raw <= min_bid_for_adv
    return _MsGateSnapshot(
        current_position=pos,
        target_place=target,
        position_condition_pass=position_pass,
        current_cpm=cpm_raw,
        min_bid=min_bid_for_adv,
        min_bid_condition_pass=min_bid_pass,
    )


def _cost_gate_fields(
    keyword_pay_for_order: float | None,
    resolved_target_cost: float | None,
) -> tuple[bool, bool | None, str | None]:
    """cost_gate_evaluated, cost_condition_pass, reason_no_data для missing inputs."""
    if keyword_pay_for_order is None:
        return False, None, "нет PFO"
    if resolved_target_cost is None:
        return False, None, "нет threshold"
    return True, keyword_pay_for_order <= resolved_target_cost, None


def _build_ms_diagnostic(
    *,
    returned_state: KeywordState,
    diagnostic_state: AboveTargetMinBidDiagnosticState,
    gates: _MsGateSnapshot,
    keyword_pay_for_order: float | None,
    resolved_target_cost: float | None,
    cost_gate_evaluated: bool,
    cost_condition_pass: bool | None,
    cooldown_elapsed_hours: float | None = None,
    reason_no_data: str | None = None,
) -> AboveTargetMinBidDiagnostic:
    return AboveTargetMinBidDiagnostic(
        state=diagnostic_state,
        current_position=gates.current_position,
        target_place=gates.target_place,
        position_condition_pass=gates.position_condition_pass,
        current_cpm=gates.current_cpm,
        min_bid=gates.min_bid,
        min_bid_condition_pass=gates.min_bid_condition_pass,
        pay_for_order=keyword_pay_for_order,
        resolved_target_cost=resolved_target_cost,
        cost_gate_evaluated=cost_gate_evaluated,
        cost_condition_pass=cost_condition_pass,
        cooldown_display_tag=returned_state.cooldown_display_tag,
        cooldown_elapsed_hours=cooldown_elapsed_hours,
        reason_no_data=reason_no_data,
        resulting_status=returned_state.status,
        resulting_reason=returned_state.reason,
    )


def _attach_ms_diagnostic(
    returned_state: KeywordState, diagnostic: AboveTargetMinBidDiagnostic
) -> KeywordState:
    return returned_state.model_copy(update={"above_target_min_bid": diagnostic})


def _blocked_diagnostic_context(
    *,
    gates: _MsGateSnapshot,
    keyword_pay_for_order: float | None,
    resolved_target_cost: float | None,
    returned_state: KeywordState,
    cooldown_elapsed_hours: float | None = None,
) -> AboveTargetMinBidDiagnostic:
    evaluated, cost_pass, missing_reason = _cost_gate_fields(
        keyword_pay_for_order, resolved_target_cost
    )
    return _build_ms_diagnostic(
        returned_state=returned_state,
        diagnostic_state=AboveTargetMinBidDiagnosticState.BLOCKED,
        gates=gates,
        keyword_pay_for_order=keyword_pay_for_order,
        resolved_target_cost=resolved_target_cost,
        cost_gate_evaluated=evaluated,
        cost_condition_pass=cost_pass,
        cooldown_elapsed_hours=cooldown_elapsed_hours,
        reason_no_data=missing_reason,
    )


def _retest_diagnostic_context(
    *,
    gates: _MsGateSnapshot,
    keyword_pay_for_order: float | None,
    resolved_target_cost: float | None,
    returned_state: KeywordState,
    cooldown_elapsed_hours: float | None = None,
) -> AboveTargetMinBidDiagnostic:
    """Diagnostic для TEMPORARY_RECHECK: cost gate как при входе в cooldown."""
    evaluated, cost_pass, missing_reason = _cost_gate_fields(
        keyword_pay_for_order, resolved_target_cost
    )
    return _build_ms_diagnostic(
        returned_state=returned_state,
        diagnostic_state=AboveTargetMinBidDiagnosticState.TEMPORARY_RECHECK,
        gates=gates,
        keyword_pay_for_order=keyword_pay_for_order,
        resolved_target_cost=resolved_target_cost,
        cost_gate_evaluated=evaluated,
        cost_condition_pass=cost_pass,
        cooldown_elapsed_hours=cooldown_elapsed_hours,
        reason_no_data=missing_reason,
    )


def _missing_ms_inputs_reason(
    *,
    min_bid_for_adv: int | None,
    cooldown_map: Mapping[str, datetime | AboveTargetCooldownEntry | None] | None,
    cooldown_updates: dict[str, AboveTargetCooldownEntry | None] | None,
    now: datetime | None,
) -> str:
    """Человекочитаемое объяснение для NO_DATA (без имён аргументов apply)."""
    parts: list[str] = []
    if min_bid_for_adv is None:
        parts.append("мин. ставки WB")
    if cooldown_map is None or cooldown_updates is None:
        parts.append("состояния cooldown МС")
    if now is None:
        parts.append("времени расчёта")
    return "нет " + ", ".join(parts)


def apply_above_target_min_bid_cooldown(
    *,
    pre_kw: PreCalculatedKeyword,
    base_state: KeywordState,
    min_bid_for_adv: int | None,
    keyword_pay_for_order: float | None,
    resolved_target_cost: float | None,
    cooldown_map: Mapping[str, datetime | AboveTargetCooldownEntry | None] | None,
    cooldown_updates: dict[str, AboveTargetCooldownEntry | None] | None,
    now: datetime | None,
) -> KeywordState:
    """Перекрывает base_state по правилу; ALWAYS_ON (hard_status 4) не трогаем."""
    gates = _ms_gate_snapshot(pre_kw, min_bid_for_adv)

    if pre_kw.hard_status == 4:
        diag = _build_ms_diagnostic(
            returned_state=base_state,
            diagnostic_state=AboveTargetMinBidDiagnosticState.INACTIVE,
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            cost_gate_evaluated=False,
            cost_condition_pass=None,
            reason_no_data="ФФ",
        )
        return _attach_ms_diagnostic(base_state, diag)

    if (
        min_bid_for_adv is None
        or cooldown_map is None
        or cooldown_updates is None
        or now is None
    ):
        returned = base_state.model_copy(update={"cooldown_display_tag": None})
        diag = _build_ms_diagnostic(
            returned_state=returned,
            diagnostic_state=AboveTargetMinBidDiagnosticState.NO_DATA,
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            cost_gate_evaluated=False,
            cost_condition_pass=None,
            reason_no_data=_missing_ms_inputs_reason(
                min_bid_for_adv=min_bid_for_adv,
                cooldown_map=cooldown_map,
                cooldown_updates=cooldown_updates,
                now=now,
            ),
        )
        return _attach_ms_diagnostic(returned, diag)

    text = pre_kw.keyword_setting.text
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    # Если базовая логика уже дала GOOD и себестоимость не превышает target,
    # правило МС не должно удерживать ключ в BAD даже в окне freeze.
    if (
        base_state.status == KeywordStatus.GOOD
        and keyword_pay_for_order is not None
        and resolved_target_cost is not None
        and keyword_pay_for_order <= resolved_target_cost
    ):
        entry = _normalize_entry(cooldown_map.get(text))
        if entry is not None:
            cooldown_updates[text] = None
        returned = base_state.model_copy(update={"cooldown_display_tag": None})
        diag = _build_ms_diagnostic(
            returned_state=returned,
            diagnostic_state=AboveTargetMinBidDiagnosticState.PASS_BY_COST,
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            cost_gate_evaluated=True,
            cost_condition_pass=True,
        )
        return _attach_ms_diagnostic(returned, diag)

    # Только ключи, которые по базовой логике сейчас GOOD (активны); остальные не трогаем и не проверяем МС.
    if base_state.status != KeywordStatus.GOOD:
        entry_inactive = _normalize_entry(cooldown_map.get(text))
        if entry_inactive is not None:
            cooldown_updates[text] = None
        returned = base_state.model_copy(update={"cooldown_display_tag": None})
        diag = _build_ms_diagnostic(
            returned_state=returned,
            diagnostic_state=AboveTargetMinBidDiagnosticState.INACTIVE,
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            cost_gate_evaluated=False,
            cost_condition_pass=None,
            reason_no_data="базовый статус не GOOD",
        )
        return _attach_ms_diagnostic(returned, diag)

    condition = is_above_target_at_min_bid(pre_kw, min_bid_for_adv)
    v_cur = pre_kw.cluster_stat.views
    entry = _normalize_entry(cooldown_map.get(text))

    if entry is not None and v_cur < entry.views_at_freeze:
        cooldown_updates[text] = AboveTargetCooldownEntry(entry.last_disabled_at, v_cur)
        entry = AboveTargetCooldownEntry(entry.last_disabled_at, v_cur)

    if not condition:
        if entry is not None:
            cooldown_updates[text] = None
        returned = base_state.model_copy(update={"cooldown_display_tag": None})
        diag = _build_ms_diagnostic(
            returned_state=returned,
            diagnostic_state=AboveTargetMinBidDiagnosticState.INACTIVE,
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            cost_gate_evaluated=False,
            cost_condition_pass=None,
        )
        return _attach_ms_diagnostic(returned, diag)

    if (
        keyword_pay_for_order is not None
        and resolved_target_cost is not None
        and keyword_pay_for_order <= resolved_target_cost
    ):
        if entry is not None:
            cooldown_updates[text] = None
        returned = base_state.model_copy(update={"cooldown_display_tag": None})
        diag = _build_ms_diagnostic(
            returned_state=returned,
            diagnostic_state=AboveTargetMinBidDiagnosticState.PASS_BY_COST,
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            cost_gate_evaluated=True,
            cost_condition_pass=True,
        )
        return _attach_ms_diagnostic(returned, diag)

    if entry is None:
        cooldown_updates[text] = AboveTargetCooldownEntry(now, v_cur)
        returned = KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )
        diag = _blocked_diagnostic_context(
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            returned_state=returned,
        )
        return _attach_ms_diagnostic(returned, diag)

    last = entry.last_disabled_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    else:
        last = last.astimezone(UTC)
    if now.tzinfo is None:
        now_utc = now.replace(tzinfo=UTC)
    else:
        now_utc = now.astimezone(UTC)

    elapsed = now_utc - last
    elapsed_h = elapsed.total_seconds() / 3600.0
    v_fixed = entry.views_at_freeze
    threshold_end = _FREEZE_H + _WAIT_AFTER_FREEZE_H + _RETEST_WINDOW_H

    if elapsed < _FREEZE_H + _WAIT_AFTER_FREEZE_H:
        returned = KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )
        diag = _blocked_diagnostic_context(
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            returned_state=returned,
            cooldown_elapsed_hours=elapsed_h,
        )
        return _attach_ms_diagnostic(returned, diag)

    if elapsed < threshold_end:
        if v_cur > v_fixed:
            returned = base_state.model_copy(
                update={"cooldown_display_tag": COOLDOWN_RETEST_DISPLAY_TAG}
            )
            diag = _retest_diagnostic_context(
                gates=gates,
                keyword_pay_for_order=keyword_pay_for_order,
                resolved_target_cost=resolved_target_cost,
                returned_state=returned,
                cooldown_elapsed_hours=elapsed_h,
            )
            return _attach_ms_diagnostic(returned, diag)
        returned = KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )
        diag = _blocked_diagnostic_context(
            gates=gates,
            keyword_pay_for_order=keyword_pay_for_order,
            resolved_target_cost=resolved_target_cost,
            returned_state=returned,
            cooldown_elapsed_hours=elapsed_h,
        )
        return _attach_ms_diagnostic(returned, diag)

    cooldown_updates[text] = AboveTargetCooldownEntry(now, v_cur)
    returned = KeywordState(
        status=KeywordStatus.BAD,
        reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
        best_keyword_status=base_state.best_keyword_status,
        cooldown_display_tag=None,
    )
    diag = _blocked_diagnostic_context(
        gates=gates,
        keyword_pay_for_order=keyword_pay_for_order,
        resolved_target_cost=resolved_target_cost,
        returned_state=returned,
        cooldown_elapsed_hours=elapsed_h,
    )
    return _attach_ms_diagnostic(returned, diag)
