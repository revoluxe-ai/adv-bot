from app.core.wb_api.base import BaseAPI
from app.core.wb_api.mixins.adv import AdvMixin
from app.core.wb_api.mixins.content import ContentMixin
from app.core.wb_api.mixins.statistic_mixin import CommonStatMinix


class WBApi(BaseAPI, AdvMixin, ContentMixin, CommonStatMinix):
    pass
