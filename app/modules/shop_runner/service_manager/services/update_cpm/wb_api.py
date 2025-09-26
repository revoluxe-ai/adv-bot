"""Утилитарный WB API клиент для обновления CPM."""

__all__ = ("WBApi",)

from app.core.mp.wb.base_wb_api_manager import BaseWBApiManager
from app.core.mp.wb.mixins import CPMUpdateMixin
from app.core.mp.wb.mixins.min_bid_mixin import MinBidMixin


class WBApi(CPMUpdateMixin, MinBidMixin, BaseWBApiManager):
    pass
