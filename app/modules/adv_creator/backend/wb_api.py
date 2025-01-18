from app.core.wb_api.base import InterfaceWBAPI
from app.core.wb_api.mixins.adv import AdvMixin
from app.core.wb_api.mixins.content import ContentMixin


class WBApi(
    # InterfaceWBAPI,
            AdvMixin,
            ContentMixin
            ):
    pass