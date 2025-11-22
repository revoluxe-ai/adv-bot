# Compatibility stub for AutoAdv
from app.modules.common_slaves.wildberries.data_classes.adv import Adv


class AutoAdv(Adv):
    # TODO: Тут ошибка в рантайме!
    @property
    def cpm(self) -> int:
        try:
            return int(self.data["autoParams"]["cpm"])
        except KeyError as e:
            raise e

__all__ = ["AutoAdv"]
