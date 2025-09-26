"""
Commands for scheduling CPM bid updates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(slots=True)
class BidUpdateForNmidCommand:
    """Single NMID bid update used by legacy flows."""

    adv_id: int
    nmid: int
    new_bid: int

    def __post_init__(self) -> None:
        if self.new_bid < 0:
            raise ValueError(f"new_bid must be non-negative, got {self.new_bid}")
        if self.adv_id <= 0:
            raise ValueError(f"adv_id must be positive, got {self.adv_id}")
        if self.nmid <= 0:
            raise ValueError(f"nmid must be positive, got {self.nmid}")


@dataclass(slots=True)
class NmCpmBid:
    """Atomic bid update for a single nm used in bulk commands."""

    nm: int
    cpm: int

    def __post_init__(self) -> None:
        if self.nm <= 0:
            raise ValueError(f"nm must be positive, got {self.nm}")
        if self.cpm < 0:
            raise ValueError(f"cpm must be non-negative, got {self.cpm}")

    def as_dict(self) -> dict[str, int]:
        return {"nm": int(self.nm), "cpm": int(self.cpm)}


def _normalize_bids(bids: Iterable[dict[str, int] | NmCpmBid]) -> list[NmCpmBid]:
    normalized: list[NmCpmBid] = []
    for item in bids:
        if isinstance(item, NmCpmBid):
            normalized.append(item)
            continue
        try:
            nm = int(item["nm"])
            cpm = int(item["cpm"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid bid mapping: {item!r}") from exc
        normalized.append(NmCpmBid(nm=nm, cpm=cpm))
    return normalized


@dataclass(slots=True)
class UpdateBidsForShopCommand:
    """Batch of NM bids for a single advert."""

    adv_id: int
    bids: Sequence[NmCpmBid] | Sequence[dict[str, int]]

    def __post_init__(self) -> None:
        if self.adv_id <= 0:
            raise ValueError(f"adv_id must be positive, got {self.adv_id}")
        normalized = _normalize_bids(self.bids)
        if not normalized:
            raise ValueError("bids collection cannot be empty")
        self._normalized_bids = tuple(normalized)

    @property
    def normalized_bids(self) -> Sequence[NmCpmBid]:
        return self._normalized_bids

    def as_payload(self) -> list[dict[str, int]]:
        return [bid.as_dict() for bid in self._normalized_bids]
