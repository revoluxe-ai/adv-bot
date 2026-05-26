"""Unit tests for V3 hard_status <-> strategy_mode synchronization."""

from types import SimpleNamespace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
    is_v3_keyword_eligible_for_cluster_bidding,
    is_v3_status_mode_consistent,
    repaired_strategy_mode_for_v3,
    strategy_mode_for_hard_status_write_v3,
    sync_keyword_setting_mode_for_v3,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "expected"),
    [
        (0, KeywordStrategyMode.OFF),
        (1, KeywordStrategyMode.OFF),
        (2, KeywordStrategyMode.MIN_CPA),
        (3, KeywordStrategyMode.OFF),
        (4, KeywordStrategyMode.MIN_CPA),
    ],
)
def test_strategy_mode_for_hard_status_write_v3(
    hard_status: int,
    expected: KeywordStrategyMode,
) -> None:
    assert strategy_mode_for_hard_status_write_v3(hard_status) == expected


@pytest.mark.unit
def test_is_v3_campaign_only_for_version_three() -> None:
    assert is_v3_campaign(3) is True
    assert is_v3_campaign(2) is False
    assert is_v3_campaign(None) is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "strategy_mode", "expected"),
    [
        (0, KeywordStrategyMode.OFF, True),
        (1, KeywordStrategyMode.OFF, True),
        (3, KeywordStrategyMode.OFF, True),
        (2, KeywordStrategyMode.MIN_CPA, True),
        (2, KeywordStrategyMode.OPTIMUM, True),
        (2, KeywordStrategyMode.MAX_CONVERSION, True),
        (2, KeywordStrategyMode.OFF, False),
        (4, KeywordStrategyMode.MIN_CPA, True),
        (4, KeywordStrategyMode.OPTIMUM, False),
    ],
)
def test_is_v3_status_mode_consistent(
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    expected: bool,
) -> None:
    assert (
        is_v3_status_mode_consistent(
            hard_status=hard_status,
            strategy_mode=strategy_mode,
        )
        is expected
    )


@pytest.mark.unit
def test_repaired_strategy_mode_for_v3_keeps_consistent_active_white_list() -> None:
    assert (
        repaired_strategy_mode_for_v3(
            hard_status=2,
            strategy_mode=KeywordStrategyMode.OPTIMUM,
        )
        == KeywordStrategyMode.OPTIMUM
    )


@pytest.mark.unit
def test_repaired_strategy_mode_for_v3_fixes_white_list_off_to_min() -> None:
    assert (
        repaired_strategy_mode_for_v3(
            hard_status=2,
            strategy_mode=KeywordStrategyMode.OFF,
        )
        == KeywordStrategyMode.MIN_CPA
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "strategy_mode", "expected"),
    [
        (1, KeywordStrategyMode.OFF, False),
        (1, KeywordStrategyMode.MIN_CPA, False),
        (2, KeywordStrategyMode.MIN_CPA, True),
        (2, KeywordStrategyMode.OFF, False),
        (4, KeywordStrategyMode.MIN_CPA, True),
        (4, KeywordStrategyMode.OPTIMUM, False),
    ],
)
def test_is_v3_keyword_eligible_for_cluster_bidding(
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    expected: bool,
) -> None:
    assert (
        is_v3_keyword_eligible_for_cluster_bidding(
            hard_status=hard_status,
            strategy_mode=strategy_mode,
        )
        is expected
    )


@pytest.mark.unit
def test_sync_keyword_setting_mode_for_v3_updates_mode_for_v3_only() -> None:
    keyword_setting = SimpleNamespace(
        hard_status=1,
        strategy_mode=KeywordStrategyMode.OPTIMUM,
    )
    changed = sync_keyword_setting_mode_for_v3(
        keyword_setting,
        automatic_version=3,
        hard_status_override=1,
    )
    assert changed is True
    assert keyword_setting.strategy_mode == KeywordStrategyMode.OFF

    keyword_setting_non_v3 = SimpleNamespace(
        hard_status=1,
        strategy_mode=KeywordStrategyMode.OPTIMUM,
    )
    changed_non_v3 = sync_keyword_setting_mode_for_v3(
        keyword_setting_non_v3,
        automatic_version=2,
        hard_status_override=1,
    )
    assert changed_non_v3 is False
    assert keyword_setting_non_v3.strategy_mode == KeywordStrategyMode.OPTIMUM
