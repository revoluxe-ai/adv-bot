"""Состояние кампании на тик V3 для executors ``UpdatePipeline``."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from app.modules.shop_runner.service_manager.services.auto_updater_v3.activation_strategy import (
    ShelfClickMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.calibration_step_resolver import (
    CalibrationDirect,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.cpo_max_boundary import (
    cmp_within_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_eligibility import (
    KeywordV3Eligibility,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.rollout_aggressiveness import (
    V3RolloutAggressiveness,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
        LadderInputs,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
        SelectionPolicy,
    )


@dataclass
class AdvState:
    """Параметры кампании и gates preamble NORMAL — живут в ``UpdateContext``."""

    eligibility_by_ks_id: dict[int, KeywordV3Eligibility]
    ladder_inputs: LadderInputs
    resolve: float
    policy: SelectionPolicy
    shelf_click_mode: ShelfClickMode
    aggressiveness: V3RolloutAggressiveness
    max_pay_for_order: float
    fact_pay_for_order: float | None
    plan_fact_equal: bool
    views_equal: bool
    resolve_valid: bool
    shelf_active: bool
    guard_condition: bool
    calibration_direct: CalibrationDirect | None
    max_effective_steps: int
    configured_keyword_calibration_max_step: int
    calibration_phase_extra: dict[str, Any] = field(
        default_factory=lambda: dict[str, Any]()
    )
    guard_applied: bool = False
    v3_substitute_fact_cpo_for_max: bool = False

    @property
    def raise_cpo_ceiling(self) -> float | None:
        """SSOT потолка для raise/preamble overspend-контуров.

        При ``substitute_fact_cpo_for_max=True`` (V3 Raise MAX) потолок —
        ``max(fact, plan.max)``; иначе только plan max из БД.

        Свойство возвращает per-campaign ceiling, который используют
        preamble-executors и связанные gates. Здесь намеренно нет отдельного
        helper-а в ``update_pipeline.utils``: дублировать вычисление потолка по
        пер-ключевой логике не нужно, потому что источник истины уже живёт в
        ``AdvState``. V3 Raise MAX и Promobonus остаются независимыми флагами:
        ``max_pay_for_order`` уже может быть promo-effective, а отдельный
        глобальный cap на их композицию здесь не вводится.
        """
        if self.fact_pay_for_order is None:
            return None
        if not self.v3_substitute_fact_cpo_for_max:
            return float(self.max_pay_for_order)
        return max(float(self.fact_pay_for_order), float(self.max_pay_for_order))


    @property
    def plan_fact_changed(self) -> bool:
        return not self.plan_fact_equal

    @property
    def views_changed(self) -> bool:
        return not self.views_equal

    @property
    def calibration_in_range(self) -> bool:
        if self.fact_pay_for_order is None:
            return False
        return cmp_within_max(
            float(self.fact_pay_for_order),
            float(self.max_pay_for_order),
        )

    def copy(self) -> AdvState:
        """Поверхностная копия для ``UpdateContext.copy``."""
        return replace(self)

    def with_tick_inputs(
        self,
        *,
        eligibility_by_ks_id: dict[int, KeywordV3Eligibility],
        ladder_inputs: LadderInputs,
    ) -> AdvState:
        """Обновить eligibility/ladder после apply фазы к ledger."""
        return replace(
            self,
            eligibility_by_ks_id=eligibility_by_ks_id,
            ladder_inputs=ladder_inputs,
        )

    @classmethod
    def empty(cls) -> AdvState:
        """Минимальный state для unit-тестов без полного preamble."""
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_ladder_view import (
            LadderInputs,
        )
        from app.modules.shop_runner.service_manager.services.auto_updater_v3.transition_ranking import (
            SelectionPolicy,
        )

        return cls(
            eligibility_by_ks_id={},
            ladder_inputs=LadderInputs.from_contexts([]),
            resolve=0.0,
            policy=SelectionPolicy.from_aggressiveness(
                click_mode=ShelfClickMode.ORGANIC_DOMINANT,
                aggressiveness=V3RolloutAggressiveness.MID,
            ),
            shelf_click_mode=ShelfClickMode.ORGANIC_DOMINANT,
            aggressiveness=V3RolloutAggressiveness.MID,
            max_pay_for_order=0.0,
            fact_pay_for_order=None,
            plan_fact_equal=True,
            views_equal=True,
            resolve_valid=False,
            shelf_active=False,
            guard_condition=False,
            calibration_direct=None,
            max_effective_steps=1,
            configured_keyword_calibration_max_step=1,
        )
