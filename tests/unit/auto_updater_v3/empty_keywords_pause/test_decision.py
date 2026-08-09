"""Unit: decision helpers для pause-on-empty-keywords (tests-first).

Spec: ``pause-on-empty-keywords``.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    V3Action,
    V3ActionType,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.empty_keywords_pause.decision import (
    STATS_WINDOW_DAYS_MAX,
    count_active_keywords,
    had_force_off_action,
    is_empty_keywords_reason,
    should_request_empty_keywords_pause_intent,
    stats_window_compatible_with_recheck,
)
from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AutoReasonCode,
)


def _kw(mode: KeywordStrategyMode) -> MagicMock:
    kw = MagicMock()
    kw.strategy_mode = mode
    return kw


@pytest.mark.unit
def test_count_active_keywords_characterization_empty_and_non_empty() -> None:
    """Characterization/spec: активные = не OFF; 0 → empty set."""
    assert count_active_keywords([]) == 0
    assert count_active_keywords([_kw(KeywordStrategyMode.OFF)]) == 0
    assert (
        count_active_keywords(
            [_kw(KeywordStrategyMode.OFF), _kw(KeywordStrategyMode.OPTIMUM)]
        )
        == 1
    )


@pytest.mark.unit
def test_had_force_off_action() -> None:
    """Текущий шаг OFF детектится по FORCE_OFF в post-gate actions."""
    assert had_force_off_action([]) is False
    assert had_force_off_action(None) is False
    off = V3Action(
        action=V3ActionType.FORCE_OFF,
        keyword_setting_id=1,
        reason="t",
    )
    assert had_force_off_action([off]) is True


@pytest.mark.unit
def test_should_request_intent_after_last_off_next_step_not_current() -> None:
    """Spec: выключать больше нечего → intent на pause как следующий шаг."""
    assert (
        should_request_empty_keywords_pause_intent(
            active_count=0,
            bot_active=True,
            bot_driven_off_completed=True,
            campaign_is_started=False,
        )
        is True
    )


@pytest.mark.unit
def test_should_not_request_intent_while_keys_remain() -> None:
    """Paired negative: ещё есть что выключать → intent не ставим."""
    assert (
        should_request_empty_keywords_pause_intent(
            active_count=1,
            bot_active=True,
            bot_driven_off_completed=True,
            campaign_is_started=True,
        )
        is False
    )


@pytest.mark.unit
def test_should_not_request_intent_when_already_paused_without_off() -> None:
    """Не блокируем recheck: на паузе без нового OFF intent не ставим."""
    assert (
        should_request_empty_keywords_pause_intent(
            active_count=0,
            bot_active=True,
            bot_driven_off_completed=False,
            campaign_is_started=False,
        )
        is False
    )


@pytest.mark.unit
def test_should_request_intent_when_started_and_still_empty_recheck() -> None:
    """После recheck-start при пустом наборе снова нужен pause-intent."""
    assert (
        should_request_empty_keywords_pause_intent(
            active_count=0,
            bot_active=True,
            bot_driven_off_completed=False,
            campaign_is_started=True,
        )
        is True
    )


@pytest.mark.unit
def test_should_not_request_intent_on_warmup_false_empty() -> None:
    """ROOT-001 / §7.2: warmup ``__empty__`` blocks no-prior-intent arm only."""
    assert (
        should_request_empty_keywords_pause_intent(
            active_count=0,
            bot_active=True,
            bot_driven_off_completed=False,
            campaign_is_started=True,
            is_warmup_false_empty=True,
        )
        is False
    )
    # Bot-driven OFF is settled empty — warmup flag must not cancel it.
    assert (
        should_request_empty_keywords_pause_intent(
            active_count=0,
            bot_active=True,
            bot_driven_off_completed=True,
            campaign_is_started=False,
            is_warmup_false_empty=True,
        )
        is True
    )


@pytest.mark.unit
def test_empty_keywords_reason_distinct_from_schedule_budget() -> None:
    """Spec Distinct pause reason: empty_keywords ≠ schedule/budget/cost."""
    from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager import (
        AuctionReasonCode,
    )

    assert is_empty_keywords_reason(AutoReasonCode.EMPTY_KEYWORDS) is True
    assert is_empty_keywords_reason(AuctionReasonCode.EMPTY_KEYWORDS) is True
    assert is_empty_keywords_reason(AutoReasonCode.TIME_SCHEDULE) is False
    assert is_empty_keywords_reason(AutoReasonCode.COMMON_SPEND_EXCEEDED) is False
    assert is_empty_keywords_reason(AutoReasonCode.COST_RULE_FAILED) is False
    assert is_empty_keywords_reason(AutoReasonCode.INSUFFICIENT_BALANCE) is False
    assert is_empty_keywords_reason(SimpleNamespace(value="empty_keywords")) is True


@pytest.mark.unit
def test_stats_window_7d_compatible() -> None:
    """Spec Seven-day: recheck OK при ≤7; >7 несовместим с продуктовым лимитом."""
    assert STATS_WINDOW_DAYS_MAX == 7
    assert stats_window_compatible_with_recheck(0) is True
    assert stats_window_compatible_with_recheck(7) is True
    assert stats_window_compatible_with_recheck(8) is False
