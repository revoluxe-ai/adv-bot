from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO


class UpdateCommotBidInSearchAdvsManager:


    def __init__(self, wb_manager_hub: WBManagerHub,
                 tasks_manager: TasksManager) -> None:



    async def update_common_bid_in_search_advs(self, adv: WBAdvDTO) -> None:
       new_bid = self._get_new_bid(adv)

    def _get_new_bid(self, adv: WBAdvDTO) -> int | None:
        result_target_pay_for_order = adv.result_target_pay_for_order
        fact_pay_for_order = adv.fact_pay_for_order
        current_bid = adv.search_cpm
        bid_step: int = adv.bid_step
        if not current_bid:
            return None
        max_cpm_by_keywords: int | None = self._get_max_cpm_by_keywords(adv)
        if fact_pay_for_order > result_target_pay_for_order:




    def _get_max_cpm_by_keywords(self, adv: WBAdvDTO) -> float | None:
        keywords = adv.keywords
        if not keywords:
            return None
        keywords.sort(key=lambda k: k.rating_by_orders, reverse=True)
        top_key = keywords[0]
        cpm_of_top_key = top_key.cpm
        return cpm_of_top_key







