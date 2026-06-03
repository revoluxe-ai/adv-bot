"""Unit: operable keywords и hard_status ↔ strategy_mode sync."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_operable_keywords import (
    HARD_STATUS_AUTO_MODE,
    HARD_STATUS_WHITE_LIST,
    expected_hard_status_for_strategy_mode,
    filter_operable_v3_contexts,
    hard_status_matches_strategy_mode,
    is_v3_operable_hard_status,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)


def _ctx(*, ks_id: int, mode: KeywordStrategyMode, hard_status: int) -> KeywordV3Context:
    kw = CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=f"k{ks_id}",
            relevant=True,
            hard_status=hard_status,
            id=ks_id,
            strategy_mode=mode,
        ),
        cluster_stat=make_zero_keyword_stat(f"k{ks_id}"),
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=1.0,
        target_pay_for_order=None,
    )
    return KeywordV3Context(keyword=kw, position_profile=None)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("hard_status", "expected"),
    [
        (HARD_STATUS_AUTO_MODE, True),
        (HARD_STATUS_WHITE_LIST, True),
        (0, False),
        (3, False),
        (4, False),
    ],
)
def test_is_v3_operable_hard_status(hard_status: int, expected: bool) -> None:
    assert is_v3_operable_hard_status(hard_status) is expected


@pytest.mark.unit
def test_filter_operable_v3_contexts_excludes_fixed_and_manual() -> None:
    contexts = [
        _ctx(ks_id=1, mode=KeywordStrategyMode.MIN_CPA, hard_status=2),
        _ctx(ks_id=2, mode=KeywordStrategyMode.OFF, hard_status=1),
        _ctx(ks_id=3, mode=KeywordStrategyMode.OPTIMUM, hard_status=3),
        _ctx(ks_id=4, mode=KeywordStrategyMode.MAX_CONVERSION, hard_status=4),
    ]
    operable = filter_operable_v3_contexts(contexts)
    assert [c.keyword.keyword_setting_original_id for c in operable] == [1, 2]


@pytest.mark.unit
def test_expected_hard_status_for_strategy_mode() -> None:
    assert (
        expected_hard_status_for_strategy_mode(KeywordStrategyMode.OFF)
        == HARD_STATUS_AUTO_MODE
    )
    assert (
        expected_hard_status_for_strategy_mode(KeywordStrategyMode.MIN_CPA)
        == HARD_STATUS_WHITE_LIST
    )
    assert hard_status_matches_strategy_mode(
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        hard_status=HARD_STATUS_WHITE_LIST,
    )
    assert not hard_status_matches_strategy_mode(
        strategy_mode=KeywordStrategyMode.MIN_CPA,
        hard_status=HARD_STATUS_AUTO_MODE,
    )
