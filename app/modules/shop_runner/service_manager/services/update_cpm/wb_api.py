"""Утилитарный WB API клиент для обновления CPM."""

__all__ = ("WBApi",)

from app.core.mp.wb.base_wb_api_manager import BaseWBApiManager


class WBApi(mixins.CPMUpdateMixin, mixins.MinBidMixin, BaseWBApiManager):
    pass
