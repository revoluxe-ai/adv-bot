"""Дельта метрик полок между двумя снимками."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutoShelfBidDelta:
    """Приращение impressions/clicks/carts/orders/spend (current - prev)."""

    delta_impressions: int
    delta_clicks: int
    delta_carts: int
    delta_orders: int
    delta_spend: float

    def has_negative_values(self) -> bool:
        """True, если WB/CH откатили метрики (дельта < 0)."""
        return any(
            (
                self.delta_impressions < 0,
                self.delta_clicks < 0,
                self.delta_carts < 0,
                self.delta_orders < 0,
                self.delta_spend < 0,
            )
        )

    def is_zero(self) -> bool:
        """Все компоненты дельты равны нулю."""
        return (
            self.delta_impressions == 0
            and self.delta_clicks == 0
            and self.delta_carts == 0
            and self.delta_orders == 0
            and self.delta_spend == 0
        )

    def nonzero_count(self) -> int:
        """Число ненулевых компонент дельты (для логов и skip insert)."""
        return sum(
            value != 0
            for value in (
                self.delta_impressions,
                self.delta_clicks,
                self.delta_carts,
                self.delta_orders,
                self.delta_spend,
            )
        )
