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
        count_auto_keywords: int = self._count_auto_keywords(adv)
        direct: Literal['reset', 'up']
        if count_auto_keywords > 0:
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
        if adv.adv_id and bid_values:
            await self._redis_common_bid_value_manager.set_bids(adv.adv_id, bid_values)
        return None


    @staticmethod
    def _get_new_bid(adv: WBAdvDTO, current_nmid: int, direct: Literal['reset', 'up']) -> int | None:
        current_common_bids = adv.current_common_bids_in_search_adv
        current_bid: int = current_common_bids[current_nmid]
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
    def _count_auto_keywords(adv: WBAdvDTO) -> int:
        keywords = adv.keywords
        auto_keywords = sum([kw for kw in keywords if kw.hard_status == 1])
        return auto_keywords
