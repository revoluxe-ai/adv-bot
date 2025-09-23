import re

from pydantic import BaseModel

from .base_adv import Adv


class Subject(BaseModel):
    id: int
    name: str


class Active(BaseModel):
    booster: bool
    carousel: bool
    recom: bool


class AutoParams(BaseModel):
    subject: Subject
    active: Active
    nms: list[int]
    cpm: int | None = None
    nms: list[int] | None = None


class AutoAdv(Adv):
    autoParams: AutoParams

    @property
    def cpm(self) -> int:
        cpm = self.autoParams.cpm
        return cpm

    @property
    def nmids(self):
        try:
            nmids = self.autoParams.nms
            if nmids:
                return nmids
            else:
                raise Exception("NMID не найден")
        except:
            nmids = re.findall(r"(?<!\[)\d{7,9}(?!\])", self.name)
            nmids = [int(nmid) for nmid in nmids]
            return nmids if nmids else []
