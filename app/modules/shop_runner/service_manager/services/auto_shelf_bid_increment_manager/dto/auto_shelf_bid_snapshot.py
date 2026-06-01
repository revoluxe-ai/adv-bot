"""Снимок накопительных метрик полок с контекстом ставки и цены."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from .auto_shelf_bid_delta import AutoShelfBidDelta


class AutoShelfBidSnapshot(BaseModel):
    """Текущее состояние сегмента: nmid + bid + price + cumulative stat + version."""

    nmid: int
    src_ts: datetime
    mode: str
    bid_minor: int
    currency: str
    price_minor: int | None
    price_currency: str
    impressions: int
    clicks: int
    carts: int
    orders: int
    spend: float
    version: int
    bucket_start: datetime

    model_config = ConfigDict(extra="forbid")

    def event_id(self) -> str:
        """Стабильный id события (blake2b) по бизнес-полям, включая price."""
        payload = (
            self.nmid,
            self.mode,
            self.bid_minor,
            self.currency,
            self.price_minor,
            self.price_currency,
            self.impressions,
            self.clicks,
            self.carts,
            self.orders,
            self.spend,
        )
        raw = ":".join(map(str, payload)).encode("utf-8")
        return hashlib.blake2b(raw, digest_size=16).hexdigest()

    @staticmethod
    def boundary_closure_event_id(
        prev: "AutoShelfBidSnapshot",
        current: "AutoShelfBidSnapshot",
    ) -> str:
        """Idempotent ``event_id`` закрытия сегмента ``prev`` при смене контекста.

        Контекст строки — ``prev`` (bid/mode/price); в хеш входят кумулятивы на
        момент ``current.src_ts``, чтобы отличать повторные закрытия.
        """
        payload = (
            "boundary",
            prev.nmid,
            prev.mode,
            prev.bid_minor,
            prev.currency,
            prev.price_minor,
            prev.price_currency,
            current.src_ts.isoformat(),
            current.impressions,
            current.clicks,
            current.carts,
            current.orders,
            current.spend,
        )
        raw = ":".join(map(str, payload)).encode("utf-8")
        return hashlib.blake2b(raw, digest_size=16).hexdigest()

    def delta(self, prev: "AutoShelfBidSnapshot") -> AutoShelfBidDelta:
        """Дельта метрик относительно предыдущего снимка."""
        return AutoShelfBidDelta(
            delta_impressions=self.impressions - prev.impressions,
            delta_clicks=self.clicks - prev.clicks,
            delta_carts=self.carts - prev.carts,
            delta_orders=self.orders - prev.orders,
            delta_spend=self.spend - prev.spend,
        )

    def delta_nonzero_count(self, prev: "AutoShelfBidSnapshot") -> int:
        """Число ненулевых компонент дельты к prev."""
        return self.delta(prev).nonzero_count()

    def to_redis(self) -> str:
        """Сериализация для ключа last:auto_shelf_bid:{nmid}."""
        return self.model_dump_json()

    @classmethod
    def from_redis(cls, payload: str) -> Optional["AutoShelfBidSnapshot"]:
        """Десериализация из Redis; при ошибке валидации — None."""
        try:
            return cls.model_validate_json(payload)
        except ValidationError:
            return None

    @classmethod
    def from_clickhouse(cls, row: dict[str, Any]) -> "AutoShelfBidSnapshot":
        """Сборка из строки auto_shelf_bid_prev (get_prev_auto_shelf_bid.sql)."""
        return cls(
            nmid=int(row["nmid"]),
            src_ts=row["src_ts"],
            mode=str(row["mode"]),
            bid_minor=int(row["bid_minor"]),
            currency=str(row["currency"]),
            price_minor=(
                None if row.get("price_minor") is None else int(row["price_minor"])
            ),
            price_currency=str(row.get("price_currency") or "RUB"),
            impressions=int(row["impressions"]),
            clicks=int(row["clicks"]),
            carts=int(row["carts"]),
            orders=int(row["orders"]),
            spend=float(row["spend"]),
            version=int(row["version"]),
            bucket_start=row["bucket_start"],
        )
