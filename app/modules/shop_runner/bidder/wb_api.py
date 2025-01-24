from app.core.wb_api.base import BaseAPI
from app.core.wb_api.mixins.adv import AdvMixin


class WBApi(BaseAPI,
            AdvMixin,
            ):
    pass