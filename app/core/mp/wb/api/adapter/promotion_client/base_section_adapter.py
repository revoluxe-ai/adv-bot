from app.core.mp.wb.api.adapter.abc_group_client import AbcAdapter
from app.core.mp.wb.api.adapter.sections_enum import SectionsEnum


class BaseSectionAdapter(AbcAdapter):
    section = SectionsEnum.PROMOTION
