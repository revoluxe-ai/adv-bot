from dataclasses import dataclass
from decimal import Decimal

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactSummary,
)
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost
from app.shared.domains.wb.utils.promo_plan_multiplier import EffectivePromoPlan


@dataclass
class PreComplexAdv:
    auto_adv: AdvSetting
    plan_data: PlanData | None
    plan_fact_summary: PlanFactSummary | None = None
    fact_data: FactData | None = None
    search_adv: AdvSetting | None = None
    promo_fraction: Decimal = Decimal("0")
    promo_multiplier: Decimal = Decimal("1")
    effective_promo_plan: EffectivePromoPlan | None = None

    @property
    def resolved_target_pay_for_order(self) -> float | None:
        plan = self.plan_data
        if plan is None:
            return None
        summary = self.plan_fact_summary
        fact_predict_orders = (
            summary.fact_predict_orders if summary is not None else None
        )
        return resolve_target_cost(
            plan.orders,
            plan.target_pay_for_order,
            plan.max_pay_for_order,
            fact_predict_orders,
        )

    @property
    def target_pay_for_order(self) -> float | None:
        """Backward-compatible alias for code paths using previous name."""
        return self.resolved_target_pay_for_order
    @property
    def adv_id(self) -> int:
        return self.auto_adv.adv_id

    @property
    def hard_min_ctr(self)-> float | None:
        return self.auto_adv.hard_min_ctr

    @property
    def original_adv_setting_id(self) -> int:
        return self.auto_adv.id

    @property
    def nmids(self) -> list[int]:
        return self.auto_adv.nmids
