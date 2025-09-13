"""Утилитарный WB API клиент для обновления CPM."""

__all__ = ("WBApi",)

from app.core.mp.wb import BaseWBApi, mixins


class WBApi(mixins.CPMUpdateMixin, mixins.MinBidMixin, BaseWBApi):
    pass
