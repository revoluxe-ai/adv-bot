from dataclasses import dataclass

from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword




@dataclass
class WBAdvDTO:
    complex_adv: ComplexAdv
    plan: PlanData
    fact: FactData
    keywords: list[CalculatedKeyword]
    min_bids: AdvMinNmidsBids
    current_common_bids_in_search_adv: dict[int, int] # артикул ->  ставка



    @property
    def result_target_pay_for_order(self) -> int:
        fact_orders = self.fact.predict_orders
        plan_orders = self.plan.orders
        if fact_orders >= plan_orders:
            return self.plan.target_pay_for_order
        else:
            return self.plan.max_pay_for_order


    @property
    def fact_pay_for_order(self) -> float:
        return self.fact.pay_for_order


    @property
    def search_cpm(self) -> int | None:
        return self.complex_adv.search_cpm


    @property
    def bid_step(self) -> int:
        return self.complex_adv.bid_cpm_step



