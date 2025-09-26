from app.core.mp.wb.base_wb_api import BaseWBApi
from app.core.mp.wb.mixins.cpm_update_mixin import CPMUpdateMixin


class WBApiCpmUpdater(CPMUpdateMixin, BaseWBApi):
    pass
