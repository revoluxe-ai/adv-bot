from typing import Literal

from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
    SetCommonBidsCommandItem,
)
from app.core.mp.wb.api.managers.wb_promotion_manager.wb_promotion_manager import WBModifier
from app.modules.shop_runner.tasks_manager.tasks_manager import TasksManager
from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.redis_common_bid_value_manager import (
    RedisCommonBidValueManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.shared.domains.wb.enums import AdvType


class UpdateCommotBidInSearchAdvsManager:
    def __init__(
        self,
        wb_modifier: WBModifier,
        tasks_manager: TasksManager,
        redis_common_bid_value_manager: RedisCommonBidValueManager,
    ) -> None:
        # keep modifier/data manager handles for bid updates, and task runner for future steps
        self._wb_modifier: WBModifier = wb_modifier
        self._tasks_manager = tasks_manager
        self._redis_common_bid_value_manager = redis_common_bid_value_manager

    async def update_common_bid_in_search_adv(self, adv: WBAdvDTO) -> None:
        count_auto_keywords: int = await self._count_candidate_to_keywords(adv)
        direct: Literal['reset', 'up']
        if count_auto_keywords > 0:
            direct = 'reset'
        else:
            # leg-cpo-economics: Search common-bid belongs to Search leg.
            fact_pay_for_order: float | None = adv.search_fact_cpo
            if fact_pay_for_order is None:
                direct = 'reset'
            # TODO: Вынести этот коэффициент в общий настраиваемый grace-период
            elif fact_pay_for_order >= adv.result_target_pay_for_order * 0.9:
                direct = 'reset'
            else:
                direct = 'up'

        nmids: list[int] = adv.nmids
        nmid_to_new_bid: dict[int, int | None] = {}

        for nmid in nmids:
            new_bid = self._get_new_bid(adv, current_nmid=nmid, direct=direct)
            nmid_to_new_bid[nmid] = new_bid

        command_items = self._build_command_items(adv, nmid_to_new_bid)
        if not command_items:
            return None

        command = SetCommonBidsCommand(items=command_items)
        await self._wb_modifier.update_search_adv_common_cpm(command)
        bid_values: dict[int, int] = {
            item.target_nmid: int(item.new_bid)
            for item in command_items
            if item.new_bid is not None
        }
        search_adv_id = adv.complex_adv.search_adv_id
        if search_adv_id is not None and bid_values:
            await self._redis_common_bid_value_manager.set_bids(search_adv_id, bid_values)
        return None


    @staticmethod
    def _get_new_bid(adv: WBAdvDTO, current_nmid: int, direct: Literal['reset', 'up']) -> int | None:
        current_common_bids = adv.current_common_bids_in_search_adv
        if current_common_bids is not None and current_nmid in current_common_bids:
            current_bid = current_common_bids[current_nmid]
        else:
            current_bid = adv.search_adv_min_bids[current_nmid]
        if not current_bid:
            return None
        if direct == 'up':
            bid_step: int = 1
            new_bid = current_bid + bid_step
        elif direct == 'reset':
            new_bid = adv.search_adv_min_bids[current_nmid]
        else:
            raise ValueError(f"Invalid direct: {direct}")
        min_bid = adv.search_adv_min_bids[current_nmid]
        if new_bid < min_bid:
            new_bid = min_bid
        max_bid = adv.max_user_cpm_bid
        if new_bid > max_bid:
            new_bid = max_bid
        if new_bid == current_bid:
            return None
        return int(new_bid)

    @staticmethod
    def _get_max_cpm_by_keywords(adv: WBAdvDTO) -> float | None:
        keywords = adv.keywords
        if not keywords:
            return None
        keywords.sort(key=lambda k: k.rating or 0, reverse=True)
        top_key = keywords[0]
        cpm_of_top_key = top_key.cpm
        return cpm_of_top_key

    @staticmethod
    def _build_command_items(
        adv: WBAdvDTO, nmid_to_new_bid: dict[int, int | None]
    ) -> list[SetCommonBidsCommandItem]:
        return [
            SetCommonBidsCommandItem(
                complex_adv=adv.complex_adv,
                adv_type=AdvType.SEARCH,
                target_nmid=nmid,
                new_bid=new_bid,
            )
            for nmid, new_bid in nmid_to_new_bid.items()
            if new_bid is not None
        ]
    @staticmethod
    async def _count_candidate_to_keywords(adv: WBAdvDTO) -> int:
        from app.modules.keywords_manager.keywords_manager import KeywordsManager
        keywords_manager = KeywordsManager()
        candidates: list[CalculatedKeyword] = await keywords_manager.get_candidates_to_white_list(adv.complex_adv)
        auto_keywords = len(candidates)
        return auto_keywords
