"""Логика цикла 24 ч BAD / 1 ч перетест для ключей выше цели при мин. ставке."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.core.mp.wb.dto import AdvMinNmidsBids
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

_COOLDOWN_24H = timedelta(hours=24)
_COOLDOWN_25H = timedelta(hours=25)

# Метка окна перетеста (24–25 ч) для UI / логов
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


def apply_above_target_min_bid_cooldown(
    *,
    pre_kw: PreCalculatedKeyword,
    base_state: KeywordState,
    min_bid_for_adv: int | None,
    cooldown_map: dict[str, datetime | None] | None,
    cooldown_updates: dict[str, datetime | None] | None,
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
        return base_state

    text = pre_kw.keyword_setting.text
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)

    condition = is_above_target_at_min_bid(pre_kw, min_bid_for_adv)
    last = cooldown_map.get(text)

    if not condition:
        if last is not None:
            cooldown_updates[text] = None
        return base_state.model_copy(update={"cooldown_display_tag": None})

    # condition True
    if last is None or (now - last) >= _COOLDOWN_25H:
        cooldown_updates[text] = now
        return KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )

    elapsed = now - last
    if elapsed < _COOLDOWN_24H:
        return KeywordState(
            status=KeywordStatus.BAD,
            reason=KeywordStatusReason.ABOVE_TARGET_AT_MIN_BID,
            best_keyword_status=base_state.best_keyword_status,
            cooldown_display_tag=None,
        )

    if _COOLDOWN_24H <= elapsed < _COOLDOWN_25H:
        return base_state.model_copy(update={"cooldown_display_tag": COOLDOWN_RETEST_DISPLAY_TAG})

    return base_state
