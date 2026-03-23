"""Логика cooldown «выше цели при мин. ставке»: 24 ч заморозка, затем 1 ч ожидание + ≥1 показ, окно перетеста 25–26 ч."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
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
    """Максимум мин. CPM поиска по артикулам комплекса; None если нечего сравнивать."""
    if not nmids or min_bids is None or not min_bids.search:
        return None
    values = [min_bids.search.get(nmid, 0) for nmid in nmids]
    m = max(values)
    if m <= 0:
        return None
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


def apply_above_target_min_bid_cooldown(
    *,
    pre_kw: PreCalculatedKeyword,
    base_state: KeywordState,
    min_bid_for_adv: int | None,
    cooldown_map: Mapping[str, datetime | AboveTargetCooldownEntry | None] | None,
    cooldown_updates: dict[str, AboveTargetCooldownEntry | None] | None,
    now: datetime | None,
) -> KeywordState:
    """Перекрывает base_state по правилу; ALWAYS_ON (hard_status 4) не трогаем."""
    if pre_kw.hard_status == 4:
        return base_state

    if (
        min_bid_for_adv is None
        or cooldown_map is None
        or cooldown_updates is None
        or now is None
    ):
        return base_state.model_copy(update={"cooldown_display_tag": None})

    text = pre_kw.keyword_setting.text
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    condition = is_above_target_at_min_bid(pre_kw, min_bid_for_adv)
    v_cur = pre_kw.cluster_stat.views

    entry = _normalize_entry(cooldown_map.get(text))

    if entry is not None and v_cur < entry.views_at_freeze:
        cooldown_updates[text] = AboveTargetCooldownEntry(entry.last_disabled_at, v_cur)
        entry = AboveTargetCooldownEntry(entry.last_disabled_at, v_cur)

    if not condition:
        if entry is not None:
            cooldown_updates[text] = None
        return base_state.model_copy(update={"cooldown_display_tag": None})

    if entry is None:
        cooldown_updates[text] = AboveTargetCooldownEntry(now, v_cur)
        return KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )

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
    v_fixed = entry.views_at_freeze
    threshold_end = _FREEZE_H + _WAIT_AFTER_FREEZE_H + _RETEST_WINDOW_H

    if elapsed < _FREEZE_H + _WAIT_AFTER_FREEZE_H:
        return KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )

    if elapsed < threshold_end:
        if v_cur > v_fixed:
            return base_state.model_copy(
                update={"cooldown_display_tag": COOLDOWN_RETEST_DISPLAY_TAG}
            )
        return KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )

    cooldown_updates[text] = AboveTargetCooldownEntry(now, v_cur)
    return KeywordState(
        status=KeywordStatus.BAD,
        reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
        best_keyword_status=base_state.best_keyword_status,
        cooldown_display_tag=None,
    )
