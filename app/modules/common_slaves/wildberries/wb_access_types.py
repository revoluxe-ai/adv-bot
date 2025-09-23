from dataclasses import dataclass
from typing import List, Optional

from .models import WBToken, WBUserCabinet, WBCabinet


@dataclass
class WBCabinetAccess:
    tokens: List[WBToken]
    wb_user_cabinet: Optional[WBUserCabinet]
    wb_cabinet: Optional[WBCabinet]

    @property
    def shop_id(self) -> str:
        if self.wb_cabinet and hasattr(self.wb_cabinet, "shop_id"):
            return str(self.wb_cabinet.shop_id)
        if self.tokens and hasattr(self.tokens[0], "shop_id"):
            return str(self.tokens[0].shop_id)
        raise AttributeError("shop_id is not available in WBCabinetAccess")
