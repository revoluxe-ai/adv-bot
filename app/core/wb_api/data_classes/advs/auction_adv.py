from typing import Optional

from pydantic import BaseModel

from .base_adv import Adv



class UnitedParams(BaseModel):
    nms: list[int]
    searchCPM: Optional[int] = None

class Multibids(BaseModel):
    nm: int
    bid: int



class AuctionAdv(Adv):
    unitedParams: Optional[list[UnitedParams]] = None
    auction_multibids: list[Multibids] | None = None


    @property
    def nmids(self) -> Optional[list[int]]:
        up = self.unitedParams
        if up:
            return up[0].nms
        else:
            return None

    @property
    def cpm(self) -> int:
        if self.auction_multibids:
            cpm =  self.auction_multibids[0].bid
            return cpm
        else:
            return self.unitedParams[0].searchCPM