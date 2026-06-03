"""Unit-тесты сортировки ключей V3 в UI (state_cost текущего режима, SSOT ladder)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.keyboards import sorting_keywords_for_v3
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
    build_prepared_from_contexts,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_eligibility_map,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
    LadderInputs,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.sort_utils import (
    resolve_v3_ui_sort_cost,
    sort_keywords_by_current_state_cost,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_state import (
    KeywordState,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
    KeywordStatusReason,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.enum import KeywordRatingMode
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_setting_dto import (
    KeywordSettingDTO,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.keyword_stat import (
    make_zero_keyword_stat,
)
from tests.unit.test_auto_updater_v3 import (
    _calc_kw,
    _conv_for_pay_for_order,
    _sample_profile,
)


def _kw(ks_id: int, orders_per_1000: float) -> CalculatedKeyword:
    text = f"k{ks_id}"
    cpm = 100.0
    conv = orders_per_1000 * cpm / 1_000_000.0
    stat = make_zero_keyword_stat(text).model_copy(
        update={"conv_views_to_orders": conv}
    )
    return CalculatedKeyword(
        adv_id=1,
        keyword_setting=KeywordSettingDTO(
            text=text,
            relevant=True,
            hard_status=1,
            id=ks_id,
            strategy_mode=KeywordStrategyMode.OFF,
        ),
        cluster_stat=stat,
        state=KeywordState(
            status=KeywordStatus.GOOD,
            reason=KeywordStatusReason.WHITE_LIST,
            best_keyword_status=False,
        ),
        rating=orders_per_1000,
        rating_mode=KeywordRatingMode.BY_MIN_CPO,
        target_pay_for_order=None,
        cpm_sources=KeywordCpmSources(cpm_set_bid=100),
    )


def _ladder_bundle(
    contexts: list[KeywordV3Context],
) -> tuple[LadderInputs, dict[int, object]]:
    prepared = build_prepared_from_contexts(contexts)
    ladder_inputs = LadderInputs.from_contexts([ctx for ctx, _ in prepared])
    elig_map = build_eligibility_map([ctx for ctx, _ in prepared])
    return ladder_inputs, elig_map


@pytest.mark.unit
def test_v3_sort_pay_for_order_fallback_without_ladder() -> None:
    """Без ladder-контекста — fallback ``pay_for_order`` asc (дешёвые сверху)."""
    kws = [_kw(1, 5.0), _kw(2, 50.0), _kw(3, 20.0)]
    sorted_kws = sorting_keywords_for_v3(kws)
    ids = [k.keyword_setting.id for k in sorted_kws]
    assert ids == [2, 3, 1]


@pytest.mark.unit
def test_v3_sort_by_state_cost_asc_two_modes() -> None:
    """OPTIMUM: меньший ``state_cost`` выше в списке."""
    prof = _sample_profile()
    cheap = _calc_kw(
        ks_id=10,
        text="alpha",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(30.0),
    )
    expensive = _calc_kw(
        ks_id=11,
        text="beta",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=_conv_for_pay_for_order(120.0),
    )
    ctx_cheap = KeywordV3Context(keyword=cheap, position_profile=prof)
    ctx_exp = KeywordV3Context(keyword=expensive, position_profile=prof)
    contexts = [ctx_exp, ctx_cheap]
    ladder_inputs, elig_map = _ladder_bundle(contexts)
    sorted_kws = sort_keywords_by_current_state_cost(
        [expensive, cheap],
        contexts,
        ladder_inputs,
        elig_map,  # type: ignore[arg-type]
    )
    assert [k.text for k in sorted_kws] == ["alpha", "beta"]


@pytest.mark.unit
def test_v3_sort_off_uses_min_state_cost_no_ch() -> None:
    """OFF сортируется по ``state_cost`` MIN (``pay_for_order`` на NO CH tier)."""
    cheap = _calc_kw(
        ks_id=20,
        text="z_last",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(40.0),
    )
    expensive = _calc_kw(
        ks_id=21,
        text="a_first",
        mode=KeywordStrategyMode.OFF,
        rating=1.0,
        conv=_conv_for_pay_for_order(90.0),
    )
    ctx_cheap = KeywordV3Context(keyword=cheap, position_profile=None)
    ctx_exp = KeywordV3Context(keyword=expensive, position_profile=None)
    contexts = [ctx_exp, ctx_cheap]
    ladder_inputs, elig_map = _ladder_bundle(contexts)
    sorted_kws = sort_keywords_by_current_state_cost(
        [expensive, cheap],
        contexts,
        ladder_inputs,
        elig_map,  # type: ignore[arg-type]
    )
    assert [k.keyword_setting.id for k in sorted_kws] == [20, 21]


@pytest.mark.unit
def test_v3_sort_no_metric_tail_alphabet() -> None:
    """Без ``state_cost`` и без PFO — в конец по ``text``."""
    prof = _sample_profile()
    with_cost = _calc_kw(
        ks_id=30,
        text="has_cost",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(50.0),
    )
    no_metric = _calc_kw(
        ks_id=31,
        text="aaa_no_data",
        mode=KeywordStrategyMode.OPTIMUM,
        rating=1.0,
        conv=0.0,
    )
    no_metric = no_metric.model_copy(
        update={
            "cluster_stat": no_metric.cluster_stat.model_copy(
                update={"conv_views_to_orders": 0.0}
            )
        }
    )
    ctx_ok = KeywordV3Context(keyword=with_cost, position_profile=prof)
    ctx_bad = KeywordV3Context(keyword=no_metric, position_profile=None)
    contexts = [ctx_ok, ctx_bad]
    ladder_inputs, elig_map = _ladder_bundle(contexts)
    assert resolve_v3_ui_sort_cost(ctx_bad, ladder_inputs, elig_map.get(31)) is None
    sorted_kws = sort_keywords_by_current_state_cost(
        [no_metric, with_cost],
        contexts,
        ladder_inputs,
        elig_map,  # type: ignore[arg-type]
    )
    assert sorted_kws[0].text == "has_cost"
    assert sorted_kws[1].text == "aaa_no_data"


@pytest.mark.unit
def test_v3_sort_tie_break_by_text() -> None:
    """Равный ``state_cost`` — tie-break по ``keyword.text``."""
    prof = _sample_profile()
    conv = _conv_for_pay_for_order(55.0)
    kw_b = _calc_kw(
        ks_id=40,
        text="b_kw",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=conv,
    )
    kw_a = _calc_kw(
        ks_id=41,
        text="a_kw",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=conv,
    )
    contexts = [
        KeywordV3Context(keyword=kw_b, position_profile=prof),
        KeywordV3Context(keyword=kw_a, position_profile=prof),
    ]
    ladder_inputs, elig_map = _ladder_bundle(contexts)
    sorted_kws = sort_keywords_by_current_state_cost(
        [kw_b, kw_a],
        contexts,
        ladder_inputs,
        elig_map,  # type: ignore[arg-type]
    )
    assert [k.text for k in sorted_kws] == ["a_kw", "b_kw"]


@pytest.mark.unit
def test_sorting_keywords_for_v3_with_ladder_delegates_ssot() -> None:
    """``sorting_keywords_for_v3`` с ladder — тот же порядок, что ``sort_keywords_by_current_state_cost``."""
    prof = _sample_profile()
    kw = _calc_kw(
        ks_id=50,
        text="solo",
        mode=KeywordStrategyMode.MIN_CPA,
        rating=1.0,
        conv=_conv_for_pay_for_order(45.0),
    )
    ctx = KeywordV3Context(keyword=kw, position_profile=prof)
    contexts = [ctx]
    ladder_inputs, elig_map = _ladder_bundle(contexts)
    via_helper = sorting_keywords_for_v3(
        [kw],
        contexts=contexts,
        ladder_inputs=ladder_inputs,
        eligibility_by_ks_id=elig_map,
    )
    via_ssot = sort_keywords_by_current_state_cost(
        [kw], contexts, ladder_inputs, elig_map  # type: ignore[arg-type]
    )
    assert via_helper == via_ssot


@pytest.mark.unit
def test_create_pre_calculated_keywords_v3_forces_min_cpo_rating() -> None:
    from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
    from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
        CalculatedKeywordsManager,
    )

    adv = MagicMock()
    adv.automatic_version = 3
    complex_adv = MagicMock()
    complex_adv.strategy = Strategy.MAX_CONV
    complex_adv.adv_setting = adv
    complex_adv.adv_id = 1

    assert (
        CalculatedKeywordsManager.resolve_keyword_rating_mode(complex_adv)
        == KeywordRatingMode.BY_MIN_CPO
    )
