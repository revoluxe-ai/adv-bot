import re

from pydantic import BaseModel, Field
from typing import cast

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
    nms: list[int] = Field(default_factory=list)
    cpm: int | None = None


class AutoAdv(Adv):
    autoParams: AutoParams

    @property
    def cpm(self) -> int:
        cpm: int | None = self.autoParams.cpm
        return cpm if cpm is not None else 0

    @property
    def nmids(self) -> list[int]:
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
