from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import WBModifier


from app.core.di.wb_manager_hub import WBManagerHub
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager, run_tasks
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO


class UpdateCommotBidInSearchAdvsManager:
    def __init__(
        self,
        wb_modifier: WBModifier ,
        tasks_manager: TasksManager,
    ) -> None:
        # keep modifier/data manager handles for bid updates, and task runner for future steps
        self._wb_modifier: WBModifier = wb_modifier
        self._tasks_manager = tasks_manager

    async def update_common_bid_in_search_advs(self, adv: WBAdvDTO) -> None:
        new_bid_pair = self._get_new_bid_pair(adv)
        if not new_bid_pair:
            return None

    def _get_new_bid_pair(self, adv: WBAdvDTO) -> int | None:
        result_target_pay_for_order = adv.result_target_pay_for_order
        fact_pay_for_order = adv.fact_pay_for_order
        current_common_bids = adv.current_common_bids_in_search_adv
        current_bid: int | None = current_common_bids.get(adv.main_nmid)
        if current_bid is None:
            current_bid = adv.search_cpm
        bid_step: int = adv.bid_step
        if not current_bid:
            return None
        max_cpm_by_keywords: int | None = self._get_max_cpm_by_keywords(adv)
        if fact_pay_for_order > result_target_pay_for_order:
            new_bid = current_bid - bid_step
        elif fact_pay_for_order < result_target_pay_for_order:
            new_bid = current_bid + bid_step
        else:
            new_bid = fact_pay_for_order
        if max_cpm_by_keywords is not None and new_bid > max_cpm_by_keywords:
            new_bid = max_cpm_by_keywords
        if new_bid < adv.min_bids[adv.main_nmid]:
            new_bid = adv.min_bids[adv.main_nmid]
        return int(new_bid)




    @staticmethod
    def _get_max_cpm_by_keywords(adv: WBAdvDTO) -> float | None:
        keywords = adv.keywords
        if not keywords:
            return None
        keywords.sort(key=lambda k: k.rating_by_orders, reverse=True)
        top_key = keywords[0]
        cpm_of_top_key = top_key.cpm
        return cpm_of_top_key







