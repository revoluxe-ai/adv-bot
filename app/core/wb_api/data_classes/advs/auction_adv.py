from pydantic import BaseModel
from typing import cast, Any

from .base_adv import Adv


class UnitedParams(BaseModel):
    nms: list[int]
    searchCPM: int | None = None


class Multibids(BaseModel):
    nm: int
    bid: int


class AuctionAdv(Adv):
    unitedParams: list[UnitedParams] | None = None
    auction_multibids: list[Multibids] | None = None

    @property
    def nmids(self) -> list[int]:
        up = self.unitedParams
        if up:
            return up[0].nms
        else:
            return []

    @property
    def cpm(self) -> int:
        if self.auction_multibids:
            cpm = self.auction_multibids[0].bid
            return cpm
        else:
            if self.unitedParams:
                return self.unitedParams[0].searchCPM if self.unitedParams[0].searchCPM is not None else 0
            return 0
