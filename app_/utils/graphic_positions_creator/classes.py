import dataclasses

from app.modules.common_slaves.wildberries.models import WBItemPosition


@dataclasses.dataclass
class CommonKeyword:
    wb_item_positions: list[WBItemPosition]
    text: str
