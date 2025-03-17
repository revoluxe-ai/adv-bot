from app.core.wb_api.mixins.adv import AdvMixin
from app.core.wb_api.mixins.adv_rights_checker import AdvRightsChecker
from app.core.wb_api.mixins.content import ContentMixin


class WBApi(
            AdvMixin,
            ContentMixin,
            AdvRightsChecker
            ):
    pass
