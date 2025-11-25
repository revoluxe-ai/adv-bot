from ..abc_group_client import AbcAdapter
from ..sections_enum import SectionsEnum


class BaseSectionAdapter(AbcAdapter):
    section = SectionsEnum.ANALYTIC_AND_DATA
