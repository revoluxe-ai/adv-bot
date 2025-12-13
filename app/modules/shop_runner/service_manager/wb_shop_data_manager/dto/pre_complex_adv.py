from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData


@dataclass
class PreComplexAdv:
    auto_adv: AdvSetting
    plan_data: PlanData
    fact_data: FactData
    search_adv: AdvSetting | None

    @property
    def target_pay_for_order(self) -> int:
        plan = self.plan_data
        fact = self.fact_data
        if fact.predict_orders >= plan.orders:
            return plan.target_pay_for_order
        else:
            return plan.max_pay_for_order
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


    @property
    def original_adv_setting_id(self) -> int:
        return self.auto_adv.id