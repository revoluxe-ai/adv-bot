"""DTO агрегированной статистики по ставке/режиму для control-контура."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class BidStatsDTO:
    """Агрегированные метрики для пары bid+mode за выбранный период.

    ВАЖНО (CPC migration v1, переименование позже):
        Поле ``cart_cpa`` — это **не** CPA корзины. В нём хранится CPC score
        ``spend / max(clicks, 1)`` для сортировки и выбора best/global_best.
        Реальный CPA корзины считайте отдельно как ``spend / max(carts, 1)``
        в месте использования (для UI/диагностики, не для выбора best bid).
        Сравнение ставок в ``pick_better_bid_by_cart_cpa`` и SQL best-bid — по CPC
        в этом поле; eligibility best — ``impressions > 0`` и ``clicks > 0``.
    """

    bid_minor: int
    currency: str
    mode: str | None
    last_interval_at: datetime | None
    impressions: int
    clicks: int
    carts: int
    orders: int
    spend: float
    cart_cpa: float | None
    ctr: float | None
    cart_cr: float | None

