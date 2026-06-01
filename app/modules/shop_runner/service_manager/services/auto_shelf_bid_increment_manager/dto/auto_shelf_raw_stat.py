"""Сырые агрегированные метрики (impressions, clicks, carts, orders, spend)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutoShelfRawStat:
    """Набор метрик за день до привязки к bid/price (total или keyword)."""

    impressions: int
    clicks: int
    carts: int
    orders: int
    spend: float

    @classmethod
    def zero(cls) -> "AutoShelfRawStat":
        """Пустая статистика (все метрики 0)."""
        return cls(
            impressions=0,
            clicks=0,
            carts=0,
            orders=0,
            spend=0.0,
        )

    def minus(self, other: "AutoShelfRawStat") -> "AutoShelfRawStat":
        """Покомпонентная разность: self - other (для total - keyword)."""
        return AutoShelfRawStat(
            impressions=self.impressions - other.impressions,
            clicks=self.clicks - other.clicks,
            carts=self.carts - other.carts,
            orders=self.orders - other.orders,
            spend=self.spend - other.spend,
        )

    def has_negative_values(self) -> bool:
        """True, если после вычитания получились отрицательные метрики."""
        return any(
            (
                self.impressions < 0,
                self.clicks < 0,
                self.carts < 0,
                self.orders < 0,
                self.spend < 0,
            )
        )
