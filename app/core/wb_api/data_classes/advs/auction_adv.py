from typing import Optional

from pydantic import BaseModel

from .base_adv import Adv



class UnitedParams(BaseModel):
    nms: list[int]
    searchCPM: Optional[int] = None



class AuctionAdv(Adv):
    unitedParams: Optional[list[UnitedParams]] = None


    @property
    def nmids(self) -> Optional[list[int]]:
        up = self.unitedParams
        if up:
            return up[0].nms
        else:
            return None

    @property
    def cpm(self) -> int:
        return self.unitedParams[0].searchCPM