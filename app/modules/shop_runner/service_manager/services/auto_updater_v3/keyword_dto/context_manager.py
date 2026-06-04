"""Менеджер ``UpdateContext``: сборка из внешних данных тика (ключи, plan/fact, профили)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto._prepared_builder import (
    assemble_update_context,
    update_context_from_prepared,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto.dto import (
    AdvState,
    KeywordsPreparedList,
    UpdateContext,
    UpdateContextInput,
    UpdateContextRuntime,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.data_update_manager.dto import (
        TickData,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
        KeywordV3Eligibility,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.selector import (
        KeywordV3Context,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
        V3TickReportCollector,
    )


class UpdateContextManager:
    """Сборка и пересборка ``UpdateContext`` из ``UpdateContextInput``."""

    def build(self, tick_input: UpdateContextInput) -> UpdateContext:
        """Собрать ``UpdateContext`` на старте preamble / pipeline."""
        contexts = self._keyword_contexts(tick_input)
        eligibility, ladder_inputs = self._tick_inputs(contexts, tick_input)
        adv_state = self._adv_state(tick_input, eligibility, ladder_inputs)
        return assemble_update_context(
            contexts,
            eligibility_by_ks_id=eligibility,
            ladder_inputs=ladder_inputs,
            adv_state=adv_state,
        )

    def build_for_tick(
        self,
        tick_data: TickData,
        *,
        tick_report: V3TickReportCollector,
    ) -> UpdateContext:
        """``UpdateContext`` для NORMAL preamble: prepared + ``runtime`` с ledger/profiles."""
        tick_input = tick_data.tick_input
        assert tick_input is not None
        contexts = list(tick_data.contexts)
        eligibility, ladder_inputs = self._tick_inputs(contexts, tick_input)
        adv_state = self._adv_state(tick_input, eligibility, ladder_inputs)
        ctx = assemble_update_context(
            contexts,
            eligibility_by_ks_id=eligibility,
            ladder_inputs=ladder_inputs,
            adv_state=adv_state,
        )
        runtime = UpdateContextRuntime(
            adv_id=int(tick_data.complex_adv.adv_id),
            tick_input=tick_input,
            ledger=tick_data.ledger,
            raw_profiles=tick_data.raw_profiles,
            tick_report=tick_report,
            contexts=list(tick_data.contexts),
            all_contexts=list(tick_data.all_contexts),
        )
        return replace(ctx, runtime=runtime)

    def from_prepared(
        self,
        prepared: KeywordsPreparedList,
        *,
        adv_state: AdvState | None = None,
    ) -> UpdateContext:
        """Обернуть ``KeywordsPreparedList`` (legacy rollout / calibration)."""
        return update_context_from_prepared(prepared, adv_state=adv_state)

    @staticmethod
    def _keyword_contexts(tick_input: UpdateContextInput) -> list[KeywordV3Context]:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_contexts import (
            build_keyword_v3_contexts,
        )

        return build_keyword_v3_contexts(tick_input.keywords, tick_input.raw_profiles)

    @staticmethod
    def _tick_inputs(
        contexts: list[KeywordV3Context],
        tick_input: UpdateContextInput,
    ) -> tuple[dict[int, KeywordV3Eligibility], LadderInputs]:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
            build_eligibility_map,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
            LadderInputs,
        )

        eligibility = build_eligibility_map(
            contexts,
            campaign_orders_per_cart_7d=tick_input.campaign_orders_per_cart_7d,
        )
        ladder_inputs = LadderInputs.from_contexts(
            contexts,
            campaign_orders_per_cart_7d=tick_input.campaign_orders_per_cart_7d,
            rec_orders_per_view=tick_input.rec_orders_per_view,
        )
        return eligibility, ladder_inputs

    @staticmethod
    def _adv_state(
        tick_input: UpdateContextInput,
        eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
        ladder_inputs: LadderInputs,
    ) -> AdvState:
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.campaign_pfo_gates import (
            FACT_OVER_MAX_DEEP_OVERSPEND_RATIO,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.resolve_threshold import (
            compute_resolve_cost_threshold,
            is_resolve_valid,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
            SelectionPolicy,
        )

        resolve = compute_resolve_cost_threshold(tick_input.plan, tick_input.fact)
        click_mode = tick_input.shelf_click_mode
        if not tick_input.shelf_active:
            click_mode = ShelfClickMode.ORGANIC_DOMINANT
        policy = SelectionPolicy.from_aggressiveness(
            click_mode=click_mode,
            aggressiveness=tick_input.aggressiveness,
        )
        fact_pfo = (
            float(tick_input.fact.pay_for_order)
            if tick_input.fact.pay_for_order is not None
            else None
        )
        guard_condition = (
            tick_input.fact.pay_for_order is not None
            and float(tick_input.fact.pay_for_order)
            > float(tick_input.plan.max_pay_for_order)
        )
        max_pfo = float(tick_input.plan.max_pay_for_order)
        deep_overspend_active = (
            fact_pfo is not None
            and max_pfo > 0
            and fact_pfo > FACT_OVER_MAX_DEEP_OVERSPEND_RATIO * max_pfo
        )
        return AdvState(
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
            resolve=resolve,
            policy=policy,
            shelf_click_mode=click_mode,
            aggressiveness=tick_input.aggressiveness,
            max_pay_for_order=float(tick_input.plan.max_pay_for_order),
            fact_pay_for_order=fact_pfo,
            plan_fact_equal=tick_input.plan_fact_equal,
            views_equal=tick_input.views_equal,
            resolve_valid=is_resolve_valid(tick_input.plan, resolve),
            shelf_active=tick_input.shelf_active,
            guard_condition=guard_condition,
            deep_overspend_active=deep_overspend_active,
            calibration_direct=tick_input.calibration_direct,
            max_effective_steps=tick_input.max_effective_steps,
            calibration_phase_extra=dict(tick_input.calibration_phase_extra),
        )
