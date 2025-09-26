from app.core.mp.wb.base_wb_api import BaseWBApi
from app.core.mp.wb.mixins.bid_update_mixin import BidUpdateMixin


class WBApiCpmUpdater(BidUpdateMixin, BaseWBApi):
    pass
