"""Каноническая идентичность физической рекламной кампании (нога)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CampaignRef:
    """
    Authority anchor кампании: физический ``advert_id`` в рамках магазина.

    ``main_nmid`` не является идентичностью кампании.
    """

    shop_id: str
    advert_id: int

    def __post_init__(self) -> None:
        if not self.shop_id:
            raise ValueError("shop_id must be non-empty")
        if self.advert_id <= 0:
            raise ValueError("advert_id must be positive")
