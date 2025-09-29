from dataclasses import dataclass
from typing import Awaitable

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting


@dataclass
class UpdateBidsInSearchAdvDTO:
    __adv_setting: "AdvSetting"
    calculated_keywords_coro: "Awaitable[list[CalculatedKeyword]]"

    @property
    def bidder_step(self) -> int:
        return self.__adv_setting.bidder_step

    @property
    def adv_id(self) -> int:
        return self.__adv_setting.search_adv_id

    @property
    def nmids(self) -> list[int]:
        return self.__adv_setting.nmids

    @property
    def max_cpm_bid(self) -> int | None:
        return self.__adv_setting.max_cpm

    @property
    def target_place(self):
        return self.__adv_setting.max_place

    def __post_init__(self):
        if not self.adv_id:
            raise ValueError("advsetting must have search_adv_id")

        if not self.nmids:
            raise ValueError("advsetting must have nmids")
