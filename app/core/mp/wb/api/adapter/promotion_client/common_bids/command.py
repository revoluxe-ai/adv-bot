from __future__ import annotations

from dataclasses import dataclass
import typing
if typing.TYPE_CHECKING:
     from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.shared.domains.wb.enums import AdvType


@dataclass(frozen=True, slots=True)
class SetCommonBidsCommandItem:
    complex_adv: "ComplexAdv"
    adv_type: AdvType
    target_nmid: int
    new_bid: float | int | None


@dataclass(frozen=True, slots=True)
class SetCommonBidsCommand:
    items: list[SetCommonBidsCommandItem]
