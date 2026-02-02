from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError


class FactStatSnapshot(BaseModel):
    METRIC_FIELDS: ClassVar[List[str]] = [
        "views_adv_sum",
        "clicks_adv_sum",
        "carts_adv_sum",
        "orders_adv_sum",
        "spend_adv_sum_rub",
        "orders_sum_adv_rub",
        "open_card_sum",
        "carts_card_sum",
        "orders_card_sum",
        "orders_sum_card_rub",
        "buy_outs_sum",
    ]

    shop_id: UUID
    complex_adv_id: int
    bucket_start: datetime
    src_ts: datetime
    version: int
    views_adv_sum: int
    clicks_adv_sum: int
    carts_adv_sum: int
    orders_adv_sum: int
    spend_adv_sum_rub: int
    orders_sum_adv_rub: int
    open_card_sum: int
    carts_card_sum: int
    orders_card_sum: int
    orders_sum_card_rub: int
    buy_outs_sum: int

    model_config = ConfigDict(extra="forbid")

    def delta(self, prev: "FactStatSnapshot") -> Dict[str, int]:
        return {
            field: getattr(self, field) - getattr(prev, field)
            for field in self.METRIC_FIELDS
        }

    def delta_nonzero_count(self, prev: "FactStatSnapshot") -> int:
        return sum(1 for value in self.delta(prev).values() if value != 0)

    def to_redis(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_redis(cls, payload: str) -> Optional["FactStatSnapshot"]:
        try:
            return cls.model_validate_json(payload)
        except ValidationError:
            return None

    @classmethod
    def from_clickhouse(cls, row: Dict[str, Any]) -> "FactStatSnapshot":
        return cls(
            shop_id=UUID(str(row["shop_id"])),
            complex_adv_id=int(row["complex_adv_id"]),
            bucket_start=row["bucket_start"],
            src_ts=row["src_ts"],
            version=int(row["version"]),
            views_adv_sum=int(row["views_adv_sum"]),
            clicks_adv_sum=int(row["clicks_adv_sum"]),
            carts_adv_sum=int(row["carts_adv_sum"]),
            orders_adv_sum=int(row["orders_adv_sum"]),
            spend_adv_sum_rub=int(row["spend_adv_sum_rub"]),
            orders_sum_adv_rub=int(row["orders_sum_adv_rub"]),
            open_card_sum=int(row["open_card_sum"]),
            carts_card_sum=int(row["carts_card_sum"]),
            orders_card_sum=int(row["orders_card_sum"]),
            orders_sum_card_rub=int(row["orders_sum_card_rub"]),
            buy_outs_sum=int(row["buy_outs_sum"]),
        )
