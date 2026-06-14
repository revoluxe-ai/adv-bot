"""Unit: NOT FULL target_place migrate и plan-fact executors."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    KeywordDTO,
    NextTargetPlace,
    UpdateContextManager,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordsPreparedList,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.keyword_v3_ladder_state import (
    KeywordV3LadderState,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto.ladder_state_kind import (
    V3LadderStageKind,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.not_full_target_place import (
    adjust_not_full_target_place_for_plan_fact,
    clamp_not_full_target_place,
    compute_not_full_target_place_delta,
    current_position_as_target_place,
    plan_fact_target_place_skip_reason,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    build_target_place_fallback_zero_by_keyword_id,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
    KeywordV3Context,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors import (
    NotFullTargetPlaceMigrateExecutor,
    NotFullTargetPlacePlanFactExecutor,
    build_normal_preamble_executors,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state import (
    manager as next_state_manager_module,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.next_state.manager import (
    NextStateManager,
)
from tests.unit.test_auto_updater_v3 import _calc_kw, _conv_for_pay_for_order


def _not_full_dto(
    *,
    ks_id: int = 1,
    mode: KeywordStrategyMode = KeywordStrategyMode.MIN_CPA,
    target_place: int | None = 0,
    position: float = 15.0,
    pay_for_order: float | None = None,
) -> KeywordDTO:
    kw = _calc_kw(
        ks_id=ks_id,
        text=f"kw{ks_id}",
        mode=mode,
        rating=1.0,
        hard_status=2,
        conv=_conv_for_pay_for_order(pay_for_order) if pay_for_order is not None else 0.0,
    )
    kw = kw.model_copy(
        update={
            "cluster_stat": kw.cluster_stat.model_copy(update={"position": position}),
        }
    )
    if target_place is not None:
        kw.keyword_setting.target_place = target_place
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    states = (
        KeywordV3LadderState(
            keyword_setting_id=ks_id,
            stage=V3LadderStageKind.OFF,
            strategy_mode=KeywordStrategyMode.OFF,
            target_position=0,
            cpo=None,
        ),
    )
    dto = KeywordDTO.from_context(ctx, ladder_states=states)
    dto.current_target_place = NextTargetPlace(
        new_target_place=0 if target_place is None else int(target_place),
        executor_name="PrepareExecutor",
    )
    return dto


@pytest.mark.unit
def test_migrate_position_minus_one() -> None:
    dto = _not_full_dto(position=15.4, target_place=0)
    assert current_position_as_target_place(dto) == 15


@pytest.mark.unit
def test_migrate_clamps_at_min() -> None:
    dto = _not_full_dto(position=1.0, target_place=0)
    assert current_position_as_target_place(dto) == 1


@pytest.mark.unit
def test_migrate_skips_when_tp_not_zero() -> None:
    dto = _not_full_dto(target_place=10, position=20.0)
    assert current_position_as_target_place(dto) == 20


@pytest.mark.unit
def test_plan_fact_adjusts_on_overspend_without_zero_reset_for_not_full_with_pfo() -> None:
    cheap = _not_full_dto(ks_id=1, position=12.0, target_place=10, pay_for_order=600.0)
    expensive = _not_full_dto(
        ks_id=2, position=12.0, target_place=10, pay_for_order=850.0
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[cheap, expensive]),
        adv_state=_legacy_context(
            fact_pay_for_order=800.0,
            max_pay_for_order=500.0,
            guard_condition=True,
        ).adv_state,
    )
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert cheap.current_target_place == 11
    assert expensive.current_target_place == 11


@pytest.mark.unit
def test_plan_fact_delta_under_and_over_threshold() -> None:
    assert compute_not_full_target_place_delta(50.0, 100.0) == -1
    assert compute_not_full_target_place_delta(90.0, 100.0) == 1
    assert compute_not_full_target_place_delta(89.9, 100.0) == -1


@pytest.mark.unit
def test_clamp_bounds() -> None:
    assert clamp_not_full_target_place(0) == 1
    assert clamp_not_full_target_place(500) == 300


@pytest.mark.unit
def test_plan_fact_skip_reason_requires_both_changes() -> None:
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = _legacy_context()
    assert plan_fact_target_place_skip_reason(ctx.adv_state) is None
    ctx2 = _legacy_context(plan_fact_equal=True, views_equal=False)
    assert plan_fact_target_place_skip_reason(ctx2.adv_state) == "plan_fact_unchanged"
    ctx3 = _legacy_context(plan_fact_equal=True, views_equal=True)
    assert (
        plan_fact_target_place_skip_reason(ctx3.adv_state)
        == "plan_fact_unchanged_and_views_unchanged"
    )


@pytest.mark.unit
def test_adjust_plan_fact_decreases_tp() -> None:
    dto = _not_full_dto(target_place=10, position=10.0, pay_for_order=50.0)
    new_place = adjust_not_full_target_place_for_plan_fact(
        dto, fact_pay_for_order=50.0, resolve=100.0
    )
    assert new_place == 9


@pytest.mark.unit
def test_adjust_plan_fact_skips_gap_tier() -> None:
    """GAP не должен получать plan-fact ±1 даже при прямом вызове helper-а."""
    dto = _not_full_dto(
        mode=KeywordStrategyMode.MIN_CPA,
        target_place=10,
        position=10.0,
        pay_for_order=None,
    )
    assert adjust_not_full_target_place_for_plan_fact(
        dto,
        fact_pay_for_order=50.0,
        resolve=100.0,
    ) is None


@pytest.mark.unit
def test_plan_fact_executor_adjusts_on_overspend_without_zero_reset() -> None:
    cheap = _not_full_dto(ks_id=1, position=12.0, target_place=10, pay_for_order=600.0)
    expensive = _not_full_dto(
        ks_id=2, position=12.0, target_place=10, pay_for_order=850.0
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[cheap, expensive]),
        adv_state=_legacy_context(
            fact_pay_for_order=800.0,
            max_pay_for_order=500.0,
            guard_condition=True,
        ).adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason is None
    assert cheap.current_target_place == 11
    assert expensive.current_target_place == 11


@pytest.mark.unit
def test_plan_fact_executor_adjusts_existing_tp_on_overspend_without_zero_reset() -> None:
    cheap = _not_full_dto(
        ks_id=1, target_place=14, position=14.0, pay_for_order=600.0
    )
    expensive = _not_full_dto(
        ks_id=2, target_place=14, position=14.0, pay_for_order=850.0
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[cheap, expensive]),
        adv_state=_legacy_context(
            fact_pay_for_order=800.0,
            max_pay_for_order=500.0,
            guard_condition=True,
        ).adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason is None
    assert cheap.current_target_place == 15
    assert expensive.current_target_place == 15


@pytest.mark.unit
def test_plan_fact_executor_does_not_reset_tp_zero_on_overspend() -> None:
    dto = _not_full_dto(target_place=14, position=14.0, pay_for_order=850.0)
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=_legacy_context(
            fact_pay_for_order=250.0, max_pay_for_order=200.0
        ).adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason is None
    assert ctx.keywords[0].current_target_place == 15


@pytest.mark.unit
def test_next_state_manager_refuses_zero_from_nf_plan_fact_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Даже ошибочный helper не должен превратить NF plan-fact в reset-в-0."""
    dto = _not_full_dto(target_place=14, position=14.0, pay_for_order=850.0)

    def _broken_plan_fact_helper(*_args: object, **_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(
        next_state_manager_module,
        "adjust_not_full_target_place_for_plan_fact",
        _broken_plan_fact_helper,
    )
    NextStateManager(
        NotFullTargetPlacePlanFactExecutor,
    ).adjust_not_full_target_place_plan_fact(
        dto,
        fact_pay_for_order=800.0,
        resolve=100.0,
    )

    assert dto.current_target_place == 14


@pytest.mark.unit
def test_fallback_zero_false_on_overspend_not_full() -> None:
    kw = _calc_kw(ks_id=6, text="nf", mode=KeywordStrategyMode.MIN_CPA, rating=1.0, hard_status=2)
    ctx = KeywordV3Context(keyword=kw, position_profile=None)
    assert build_target_place_fallback_zero_by_keyword_id([ctx]).get(6) is False


@pytest.mark.unit
def test_validate_before_migrate_non_min_gets_current_position() -> None:
    """NF validate → MIN, затем migrate: ключ не в MIN на старте тика получает текущую позицию."""
    dto = _not_full_dto(
        mode=KeywordStrategyMode.MAX_CONVERSION,
        target_place=0,
        position=12.0,
        pay_for_order=50.0,
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=_legacy_context().adv_state,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_validate import (
        NotFullValidateExecutor,
    )

    NotFullValidateExecutor().execute(ctx)
    NotFullTargetPlaceMigrateExecutor().execute(ctx)
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MIN_CPA
    assert ctx.keywords[0].current_target_place == 12


@pytest.mark.unit
def test_migrate_executor_updates_context() -> None:
    dto = _not_full_dto(position=12.0, target_place=0, pay_for_order=50.0)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=replace(
            AdvState.empty(),
            fact_pay_for_order=50.0,
            max_pay_for_order=200.0,
            resolve=100.0,
            plan_fact_equal=False,
            views_equal=False,
            resolve_valid=True,
        ),
    )
    NotFullTargetPlaceMigrateExecutor().execute(ctx)
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_target_place == 12


@pytest.mark.unit
def test_migrate_executor_skips_off_not_full_keys() -> None:
    """NOT FULL OFF не получает target_place: migrate работает только для active MIN."""
    dto = _not_full_dto(
        mode=KeywordStrategyMode.OFF,
        position=12.0,
        target_place=0,
        pay_for_order=50.0,
    )
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=replace(
            AdvState.empty(),
            fact_pay_for_order=50.0,
            max_pay_for_order=200.0,
            resolve=100.0,
            plan_fact_equal=False,
            views_equal=False,
            resolve_valid=True,
        ),
    )
    NotFullTargetPlaceMigrateExecutor().execute(ctx)
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.OFF
    assert ctx.keywords[0].current_target_place == 0


@pytest.mark.unit
def test_plan_fact_does_not_bootstrap_zero_when_migrate_cannot_run() -> None:
    """Если migrate не смог создать стартовую позицию, plan-fact не трогает sentinel 0."""
    dto = _not_full_dto(
        mode=KeywordStrategyMode.MIN_CPA,
        position=0.0,
        target_place=0,
        pay_for_order=50.0,
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=_legacy_context(
            fact_pay_for_order=50.0,
            max_pay_for_order=200.0,
            resolve=100.0,
            guard_condition=False,
        ).adv_state,
    )
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_target_place == 0


@pytest.mark.unit
def test_plan_fact_executor_does_not_reset_per_key_on_overspend() -> None:
    cheap = _not_full_dto(
        ks_id=1, target_place=10, position=10.0, pay_for_order=600.0
    )
    expensive = _not_full_dto(
        ks_id=2, target_place=10, position=10.0, pay_for_order=850.0
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[cheap, expensive]),
        adv_state=_legacy_context(
            fact_pay_for_order=800.0,
            max_pay_for_order=500.0,
            guard_condition=True,
        ).adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason is None
    assert cheap.current_target_place == 11
    assert expensive.current_target_place == 11


@pytest.mark.unit
def test_plan_fact_executor_does_not_reset_expensive_key_without_campaign_overspend() -> None:
    expensive = _not_full_dto(
        ks_id=1,
        target_place=10,
        position=10.0,
        pay_for_order=850.0,
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[expensive]),
        adv_state=_legacy_context(
            fact_pay_for_order=50.0,
            max_pay_for_order=500.0,
            resolve=100.0,
            guard_condition=True,
        ).adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason is None
    assert expensive.current_target_place == 9


@pytest.mark.unit
def test_plan_fact_executor_does_not_reset_on_campaign_cpo_boundary() -> None:
    """``fact == max`` ещё не campaign overspend, значит NF reset запрещён."""
    expensive = _not_full_dto(
        ks_id=1,
        target_place=10,
        position=10.0,
        pay_for_order=850.0,
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[expensive]),
        adv_state=_legacy_context(
            fact_pay_for_order=500.0,
            max_pay_for_order=500.0,
            resolve=100.0,
            guard_condition=True,
        ).adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason is None
    assert expensive.current_target_place == 11


@pytest.mark.unit
def test_plan_fact_executor_skips_unchanged_gate() -> None:
    dto = _not_full_dto(target_place=10, position=10.0)
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    base = _legacy_context(plan_fact_equal=True, views_equal=True)
    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=base.adv_state,
    )
    ex = NotFullTargetPlacePlanFactExecutor()
    ex.execute(ctx)
    assert ex.skip_reason == "plan_fact_unchanged_and_views_unchanged"
    assert ctx.keywords[0].current_target_place == 10


@pytest.mark.unit
def test_plan_fact_executor_skips_tp_zero_without_pfo_when_not_overspend() -> None:
    """GAP без operational PFO не должен двигаться NF plan-fact'ом."""
    dto = _not_full_dto(target_place=10, position=10.0, pay_for_order=None)
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=_legacy_context(
            fact_pay_for_order=50.0,
            max_pay_for_order=200.0,
            guard_condition=True,
        ).adv_state,
    )
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_target_place == 10


@pytest.mark.unit
def test_gap_key_does_not_get_nf_bootstrap_or_plan_fact() -> None:
    """GAP-key без operational PFO не должен попадать в NF bootstrap-контур."""
    dto = _not_full_dto(
        mode=KeywordStrategyMode.MIN_CPA,
        target_place=0,
        position=12.0,
        pay_for_order=None,
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.update_pipeline.executors.not_full_validate import (
        NotFullValidateExecutor,
    )

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=_legacy_context(
            fact_pay_for_order=50.0,
            max_pay_for_order=200.0,
            resolve=100.0,
            guard_condition=False,
        ).adv_state,
    )
    NotFullValidateExecutor().execute(ctx)
    NotFullTargetPlaceMigrateExecutor().execute(ctx)
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_mode == KeywordStrategyMode.MIN_CPA
    assert ctx.keywords[0].current_target_place == 0


@pytest.mark.unit
def test_plan_fact_executor_no_tp_zero_without_pfo_when_not_min_cpa() -> None:
    dto = _not_full_dto(
        mode=KeywordStrategyMode.MAX_CONVERSION,
        target_place=10,
        position=10.0,
        pay_for_order=None,
    )
    from tests.unit.auto_updater_v3.test_update_pipeline import _legacy_context

    ctx = UpdateContextManager().from_prepared(
        KeywordsPreparedList(keywords=[dto]),
        adv_state=_legacy_context(
            fact_pay_for_order=800.0,
            max_pay_for_order=500.0,
            guard_condition=True,
        ).adv_state,
    )
    NotFullTargetPlacePlanFactExecutor().execute(ctx)
    assert ctx.keywords[0].current_target_place == 10


@pytest.mark.unit
def test_preamble_includes_nf_tp_phases() -> None:
    names = [ex.phase_name for ex in build_normal_preamble_executors()]
    assert names[1:4] == [
        "validate_not_full_state",
        "not_full_target_place_migrate",
        "not_full_target_place_plan_fact",
    ]
