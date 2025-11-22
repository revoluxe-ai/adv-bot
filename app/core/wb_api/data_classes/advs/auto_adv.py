# Compatibility stub for AutoAdv
from app.modules.common_slaves.wildberries.data_classes.adv import Adv


class AutoAdv(Adv):
    # TODO: Тут ошибка в рантайме!
    @property
    def cpm(self) -> int | None:
        match self.data:
            case {"autoParams": {"cpm": cpm}}:
                return int(cpm)
            case {"autoParams": {"nmCPM": [{"cpm": cpm}]}}:
                return int(cpm)
            case _:
                return None


__all__ = ["AutoAdv"]
