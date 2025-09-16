from app.core.wb_api.base import BaseAPI
from app.core.wb_api.mixins.statistic_mixin import CommonStatMinix


class WBApi(CommonStatMinix,
            BaseAPI
            ):
    pass
