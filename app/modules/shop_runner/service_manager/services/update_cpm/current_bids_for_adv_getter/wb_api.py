from app.core.mp import wb


class WBApi(wb.mixins.CurrentBidMixin, wb.BaseWBApi):
    pass
