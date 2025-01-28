from app.core.wb_api.base import InterfaceWBAPI, BaseAPI
from app.core.wb_api.mixins.adv import AdvMixin
from app.core.wb_api.mixins.content import ContentMixin


class WBApi(BaseAPI,
            AdvMixin,
            ContentMixin
            ):
    pass