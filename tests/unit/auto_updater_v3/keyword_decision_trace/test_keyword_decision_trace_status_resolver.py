"""Unit: resolve_state_label / resolve_status_hint."""

from __future__ import annotations

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_decision_trace.status_resolver import (
    resolve_state_label,
    resolve_status_hint,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from tests.unit.test_auto_updater_v3 import _calc_kw


def _dto(
    ks_id: int,
    *,
    mode: KeywordStrategyMode = KeywordStrategyMode.OFF,
    hard_status: int = 1,
    status: KeywordStatus = KeywordStatus.BAD,
    profile: bool = False,
) -> "KeywordDTO":
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
        KeywordDTO,
    )
    from tests.unit.test_auto_updater_v3 import _sample_profile

    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=hard_status,
        status=status,
    )
    ctx = KeywordV3Context(
        keyword=kw,
        position_profile=_sample_profile() if profile else None,
    )
    states = (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.MIN_CPA,
            strategy_mode=KeywordStrategyMode.MIN_CPA,
            target_position=0,
            cpo=100.0,
        ),
    )
    return KeywordDTO.from_context(ctx, ladder_states=states)


@pytest.mark.unit
def test_resolve_state_gap_off() -> None:
    dto = _dto(1, mode=KeywordStrategyMode.OFF)
    dto.calculated_keyword = dto.calculated_keyword.model_copy(
        update={"cluster_stat": dto.calculated_keyword.cluster_stat.model_copy(
            update={"conv_views_to_orders": 0.0}
        )}
    )
    assert dto.data_tier.value == "gap"
    assert resolve_state_label(dto) == "GAP"


@pytest.mark.unit
def test_resolve_state_min_cpa() -> None:
    dto = _dto(2, mode=KeywordStrategyMode.MIN_CPA, profile=True)
    assert resolve_state_label(dto) == "M"


@pytest.mark.unit
def test_resolve_status_hint_off_like() -> None:
    dto = _dto(3, mode=KeywordStrategyMode.OFF, status=KeywordStatus.BAD)
    assert resolve_status_hint(dto) == "off-like"


@pytest.mark.unit
def test_resolve_status_hint_good() -> None:
    dto = _dto(
        4,
        mode=KeywordStrategyMode.MIN_CPA,
        hard_status=2,
        status=KeywordStatus.GOOD,
        profile=True,
    )
    assert resolve_status_hint(dto) == "good"
