# Compatibility stub for AutoAdv
from app.modules.common_slaves.wildberries.data_classes.adv import Adv


class AutoAdv(Adv):

    @property
    def cpm(self) -> int:
        match self.data:
            case {"autoParams": {"cpm": cpm}}:
                return int(cpm)
            case {"autoParams": {"nmCPM": [{"cpm": cpm}]}}:
                return int(cpm)
            case _:
                raise KeyError("Не найдено поле CPM в data")


__all__ = ["AutoAdv"]
