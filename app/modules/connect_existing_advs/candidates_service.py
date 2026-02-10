"""
Filter and classify v2 campaigns by nmid for «подключить существующие».
Status v2 (generated client IntEnum): allow 4, 9, 11 (ready_for_start, active, pause); exclude -1, 7, 8 (done/deleted/cancelled).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    GetAdvertsAdvertsItem,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.get_adverts_adverts_item_status import (
    GetAdvertsAdvertsItemStatus,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models.advert_settings_payment_type import (
    AdvertSettingsPaymentType,
)

logger = logging.getLogger(__name__)

# v2 status: allow only non-done (ready_for_start=4, active=9, pause=11)
ALLOWED_STATUSES = {
    GetAdvertsAdvertsItemStatus.VALUE_4,
    GetAdvertsAdvertsItemStatus.VALUE_9,
    GetAdvertsAdvertsItemStatus.VALUE_11,
}


@dataclass
class ConnectExistingCandidatesResult:
    """Candidates for connecting existing campaigns by type (auction / auto)."""

    auction_candidates: list[GetAdvertsAdvertsItem]
    auto_candidates: list[GetAdvertsAdvertsItem]


def _nm_ids_from_settings(item: GetAdvertsAdvertsItem) -> set[int]:
    """Артикулы из nm_settings и, при необходимости, из additional_properties кампании (API может отдавать nmId по-разному)."""
    out: set[int] = set()
    for ns in getattr(item, "nm_settings", []) or []:
        nid = getattr(ns, "nm_id", None)
        if nid is not None:
            out.add(int(nid))
        elif getattr(ns, "additional_properties", None):
            for key in ("nm_id", "nmId"):
                val = ns.additional_properties.get(key)
                if val is not None:
                    out.add(int(val))
                    break
    # На случай, если артикулы пришли на верхнем уровне кампании (additional_properties)
    extra = getattr(item, "additional_properties", None) or {}
    for key in ("nm_id", "nmId", "nm_ids", "nmIds"):
        val = extra.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            for v in val:
                if v is not None:
                    try:
                        out.add(int(v))
                    except (TypeError, ValueError):
                        pass
        else:
            try:
                out.add(int(val))
            except (TypeError, ValueError):
                pass
    return out


def _is_auction_campaign(item: GetAdvertsAdvertsItem) -> bool:
    """Тип 1 (аукцион): bid_type manual, размещение «в поиске» (search true), оплата CPM.
    Не требуем recommendations=false и shelf=false, чтобы не отбрасывать РК с отличиями в ответе API.
    """
    bid = (getattr(item, "bid_type", None) or "").lower()
    if bid != "manual":
        return False
    settings = getattr(item, "settings", None)
    if settings is None:
        return False
    pt = getattr(settings, "payment_type", None)
    if pt != AdvertSettingsPaymentType.CPM and str(pt).lower() != "cpm":
        return False
    p = getattr(settings, "placements", None)
    if p is None:
        return False
    search_val = getattr(p, "search", None)
    if search_val is not None:
        return bool(search_val)
    # API может вернуть search в другом регистре (additional_properties)
    extra = getattr(p, "additional_properties", None) or {}
    return bool(extra.get("search") or extra.get("Search"))


def _is_auto_campaign(item: GetAdvertsAdvertsItem) -> bool:
    """Тип 2 (авто): bid_type unified, оплата CPM. Не требуем строго search=false/shelf/recommendations — API WB может отдавать по-разному."""
    bid = (getattr(item, "bid_type", None) or "").lower()
    if bid != "unified":
        return False
    settings = getattr(item, "settings", None)
    if settings is None:
        return False
    pt = getattr(settings, "payment_type", None)
    if pt != AdvertSettingsPaymentType.CPM and str(pt).lower() != "cpm":
        return False
    return True


def filter_and_classify_campaigns_by_nmid(
    campaigns: list[GetAdvertsAdvertsItem],
    nmid: int,
) -> ConnectExistingCandidatesResult:
    """
    Filter by status (start/pause/ready_for_start), nmid, CPM; classify into auction and auto.
    """
    auction: list[GetAdvertsAdvertsItem] = []
    auto: list[GetAdvertsAdvertsItem] = []

    for item in campaigns:
        if item.status not in ALLOWED_STATUSES:
            continue
        campaign_nmids = _nm_ids_from_settings(item)
        # Включаем кампанию, если в ней есть нужный артикул (в WB может быть несколько артикулов в одной РК)
        if nmid not in campaign_nmids:
            continue
        if _is_auction_campaign(item):
            auction.append(item)
        elif _is_auto_campaign(item):
            auto.append(item)
        else:
            logger.debug(
                "connect_existing: campaign id=%s nmid=%s bid_type=%s not auction/auto",
                getattr(item, "id", None),
                nmid,
                getattr(item, "bid_type", None),
            )

    return ConnectExistingCandidatesResult(auction_candidates=auction, auto_candidates=auto)
