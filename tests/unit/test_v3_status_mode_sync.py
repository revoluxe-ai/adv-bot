"""Unit tests for V3 hard_status <-> strategy_mode synchronization."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.modules.common_slaves.wildberries.models.enums import (
    KeywordStrategyMode,
    campaign_strategy_to_keyword_strategy_mode,
)
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.shop_runner.service_manager.services.v3_status_mode_sync import (
    is_v3_campaign,
    is_v3_keyword_eligible_for_cluster_bidding,
    is_v3_status_mode_consistent,
    keyword_strategy_mode_for_adv_strategy,
    repaired_strategy_mode_for_v3,
    strategy_mode_for_hard_status_write_v3,
    sync_keyword_setting_mode_for_v3,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("adv_strategy", "expected"),
    [
        (Strategy.MIN_CPO, KeywordStrategyMode.MIN_CPA),
        (Strategy.OPTIMUM, KeywordStrategyMode.OPTIMUM),
        (Strategy.MAX_CONV, KeywordStrategyMode.MAX_CONVERSION),
        (None, KeywordStrategyMode.MIN_CPA),
    ],
)
def test_keyword_strategy_mode_for_adv_strategy(
    adv_strategy: Strategy | None,
    expected: KeywordStrategyMode,
) -> None:
    assert keyword_strategy_mode_for_adv_strategy(adv_strategy) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("adv_strategy", "expected"),
    [
        (Strategy.MIN_CPO, KeywordStrategyMode.MIN_CPA),
        (Strategy.OPTIMUM, KeywordStrategyMode.OPTIMUM),
        (Strategy.MAX_CONV, KeywordStrategyMode.MAX_CONVERSION),
        (None, KeywordStrategyMode.MIN_CPA),
    ],
)
def test_campaign_strategy_to_keyword_strategy_mode(
    adv_strategy: Strategy | None,
    expected: KeywordStrategyMode,
) -> None:
    assert campaign_strategy_to_keyword_strategy_mode(adv_strategy) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "adv_strategy", "expected"),
    [
        (0, None, KeywordStrategyMode.OFF),
        (1, Strategy.MAX_CONV, KeywordStrategyMode.OFF),
        (2, Strategy.MIN_CPO, KeywordStrategyMode.MIN_CPA),
        (2, Strategy.OPTIMUM, KeywordStrategyMode.OPTIMUM),
        (2, Strategy.MAX_CONV, KeywordStrategyMode.MAX_CONVERSION),
        (3, None, KeywordStrategyMode.OFF),
        (4, Strategy.OPTIMUM, KeywordStrategyMode.OPTIMUM),
        (4, Strategy.MAX_CONV, KeywordStrategyMode.MAX_CONVERSION),
    ],
)
def test_strategy_mode_for_hard_status_write_v3(
    hard_status: int,
    adv_strategy: Strategy | None,
    expected: KeywordStrategyMode,
) -> None:
    assert (
        strategy_mode_for_hard_status_write_v3(
            hard_status, adv_strategy=adv_strategy
        )
        == expected
    )


@pytest.mark.unit
def test_is_v3_campaign_only_for_bot_active() -> None:
    assert is_v3_campaign(True) is True
    assert is_v3_campaign(False) is False


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "strategy_mode", "adv_strategy", "expected"),
    [
        (0, KeywordStrategyMode.OFF, None, True),
        (1, KeywordStrategyMode.OFF, None, True),
        (3, KeywordStrategyMode.OFF, None, True),
        (2, KeywordStrategyMode.MIN_CPA, None, True),
        (2, KeywordStrategyMode.OPTIMUM, None, True),
        (2, KeywordStrategyMode.MAX_CONVERSION, None, True),
        (2, KeywordStrategyMode.OFF, None, False),
        (4, KeywordStrategyMode.MIN_CPA, Strategy.MIN_CPO, True),
        (4, KeywordStrategyMode.OPTIMUM, Strategy.OPTIMUM, True),
        (4, KeywordStrategyMode.MAX_CONVERSION, Strategy.MAX_CONV, True),
        (4, KeywordStrategyMode.MIN_CPA, Strategy.MAX_CONV, False),
        (4, KeywordStrategyMode.OPTIMUM, Strategy.MAX_CONV, False),
    ],
)
def test_is_v3_status_mode_consistent(
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    adv_strategy: Strategy | None,
    expected: bool,
) -> None:
    assert (
        is_v3_status_mode_consistent(
            hard_status=hard_status,
            strategy_mode=strategy_mode,
            adv_strategy=adv_strategy,
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
def test_repaired_strategy_mode_for_v3_fixes_white_list_off_to_adv_strategy() -> None:
    assert (
        repaired_strategy_mode_for_v3(
            hard_status=2,
            strategy_mode=KeywordStrategyMode.OFF,
            adv_strategy=Strategy.MAX_CONV,
        )
        == KeywordStrategyMode.MAX_CONVERSION
    )


@pytest.mark.unit
def test_repaired_strategy_mode_for_v3_fixes_fixed_to_max_conv() -> None:
    assert (
        repaired_strategy_mode_for_v3(
            hard_status=4,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            adv_strategy=Strategy.MAX_CONV,
        )
        == KeywordStrategyMode.MAX_CONVERSION
    )


@pytest.mark.unit
def test_repaired_strategy_mode_for_v3_fixes_fixed_to_optimum() -> None:
    assert (
        repaired_strategy_mode_for_v3(
            hard_status=4,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            adv_strategy=Strategy.OPTIMUM,
        )
        == KeywordStrategyMode.OPTIMUM
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "strategy_mode", "adv_strategy", "expected"),
    [
        (1, KeywordStrategyMode.OFF, None, False),
        (1, KeywordStrategyMode.MIN_CPA, None, False),
        (2, KeywordStrategyMode.MIN_CPA, None, True),
        (2, KeywordStrategyMode.OPTIMUM, None, True),
        (2, KeywordStrategyMode.OFF, None, False),
        (4, KeywordStrategyMode.MIN_CPA, Strategy.MIN_CPO, True),
        (4, KeywordStrategyMode.MAX_CONVERSION, Strategy.MAX_CONV, True),
        # ФФ с любым активным mode — eligible; adv.strategy не участвует в cluster bids.
        (4, KeywordStrategyMode.MIN_CPA, Strategy.MAX_CONV, True),
        (4, KeywordStrategyMode.OPTIMUM, Strategy.MAX_CONV, True),
        (4, KeywordStrategyMode.OFF, Strategy.MIN_CPO, False),
    ],
)
def test_is_v3_keyword_eligible_for_cluster_bidding(
    hard_status: int,
    strategy_mode: KeywordStrategyMode,
    adv_strategy: Strategy | None,
    expected: bool,
) -> None:
    assert (
        is_v3_keyword_eligible_for_cluster_bidding(
            hard_status=hard_status,
            strategy_mode=strategy_mode,
            adv_strategy=adv_strategy,
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
        bot_active=True,
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
        bot_active=False,
        hard_status_override=1,
    )
    assert changed_non_v3 is False
    assert keyword_setting_non_v3.strategy_mode == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
def test_sync_white_list_uses_adv_strategy_max_conv() -> None:
    keyword_setting = SimpleNamespace(
        hard_status=2,
        strategy_mode=KeywordStrategyMode.OFF,
    )
    changed = sync_keyword_setting_mode_for_v3(
        keyword_setting,
        bot_active=True,
        hard_status_override=2,
        adv_strategy=Strategy.MAX_CONV,
    )
    assert changed is True
    assert keyword_setting.strategy_mode == KeywordStrategyMode.MAX_CONVERSION


@pytest.mark.unit
def test_sync_fixed_uses_adv_strategy_optimum() -> None:
    keyword_setting = SimpleNamespace(
        hard_status=4,
        strategy_mode=KeywordStrategyMode.OFF,
    )
    changed = sync_keyword_setting_mode_for_v3(
        keyword_setting,
        bot_active=True,
        hard_status_override=4,
        adv_strategy=Strategy.OPTIMUM,
    )
    assert changed is True
    assert keyword_setting.strategy_mode == KeywordStrategyMode.OPTIMUM


@pytest.mark.unit
def test_sync_black_list_does_not_access_adv_setting_relationship() -> None:
    """ЧС (hard_status=0): sync не обращается к relationship adv_setting."""
    keyword_setting = MagicMock(spec=["hard_status", "strategy_mode"])
    keyword_setting.hard_status = 1
    keyword_setting.strategy_mode = KeywordStrategyMode.MIN_CPA

    changed = sync_keyword_setting_mode_for_v3(
        keyword_setting,
        bot_active=True,
        hard_status_override=0,
    )

    assert changed is True
    assert keyword_setting.strategy_mode == KeywordStrategyMode.OFF
