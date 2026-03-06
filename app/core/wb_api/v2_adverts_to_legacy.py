"""Convert GET /api/advert/v2/adverts response item to legacy dict for Adv/AuctionAdv/AutoAdv."""

from __future__ import annotations

from typing import Any


def _ts_str(value: Any) -> str:
    """Format timestamp for legacy createTime/changeTime/startTime/endTime."""
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def v2_advert_item_to_legacy(item: dict[str, Any]) -> dict[str, Any]:
    """
    Convert one item from GET /api/advert/v2/adverts response to legacy format
    expected by adv_fabric.get_adv_data_class() and Adv/AuctionAdv/AutoAdv.

    v2 item: id, bid_type (unified|manual), status, settings (name, placements),
    nm_settings (nm_id, subject, bids_kopecks.search|recommendations), timestamps.
    """
    settings = item.get("settings") or {}
    placements = settings.get("placements") or {}
    nm_settings = item.get("nm_settings") or []
    timestamps = item.get("timestamps") or {}

    bid_type = item.get("bid_type", "manual")
    legacy_type = 8 if bid_type == "unified" else 9

    # First nm_setting for subject / searchCPM / bid
    first_nm = nm_settings[0] if nm_settings else {}
    first_subject = first_nm.get("subject") or {}
    first_bids = first_nm.get("bids_kopecks") or {}

    create_time = _ts_str(timestamps.get("created"))
    updated_time = _ts_str(timestamps.get("updated"))
    started_time = _ts_str(timestamps.get("started"))
    deleted_time = _ts_str(timestamps.get("deleted"))

    # active: legacy expects booster, carousel, recom
    active = {
        "booster": False,
        "carousel": False,
        "recom": bool(placements.get("recommendations", False)),
        "search": bool(placements.get("search", False)),
    }

    # autoParams: required for Adv (category_name, subject_id, active); for type 8 also nms
    subject_dict = {"id": first_subject.get("id", 0), "name": first_subject.get("name", "")}
    auto_params: dict[str, Any] = {
        "subject": subject_dict,
        "active": active,
    }
    if legacy_type == 8:
        auto_params["nms"] = [nm.get("nm_id") for nm in nm_settings if "nm_id" in nm]
        # AutoAdv.cpm reads autoParams.cpm or autoParams.nmCPM[0].cpm
        auto_params["cpm"] = first_bids.get("search", 0) or first_bids.get("recommendations", 0)

    # unitedParams: for type 9, Adv.nmids uses unitedParams[0]["nms"]
    search_cpm_kopecks = first_bids.get("search", 0)
    united_params = [
        {
            "searchCPM": search_cpm_kopecks,
            "subject": subject_dict,
            "nms": [nm.get("nm_id") for nm in nm_settings if "nm_id" in nm],
        }
    ]

    # auction_multibids: for type 9 AuctionAdv.cpm uses auction_multibids[0]["bid"]
    auction_multibids = [{"bid": search_cpm_kopecks}] if nm_settings else [{"bid": 0}]

    status = item.get("status")
    if hasattr(status, "value"):
        status = int(status)

    legacy: dict[str, Any] = {
        "advertId": item.get("id", 0),
        "type": legacy_type,
        "name": settings.get("name", ""),
        "status": status,
        "createTime": create_time,
        "changeTime": updated_time,
        "startTime": started_time,
        "endTime": deleted_time,
        "dailyBudget": 0,
        "autoParams": auto_params,
        "unitedParams": united_params,
        "auction_multibids": auction_multibids,
    }
    return legacy
