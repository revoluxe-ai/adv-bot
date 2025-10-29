# Compatibility stub for AutoAdv
from app.modules.common_slaves.wildberries.data_classes.adv import Adv


class AutoAdv(Adv):

    @property
    def cpm(self) -> int:
        return int(self.data["autoParams"]["cpm"])


__all__ = ["AutoAdv"]
