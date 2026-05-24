"""Снимок типа РК и зон показа WB для AdvSetting (sync из v2/adverts)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import AdvSetting


def apply_wb_campaign_meta_from_legacy_adv_data(
    adv_setting: AdvSetting,
    adv_data: dict[str, Any],
) -> None:
    """Записать wb_* поля из legacy payload (после v2_adverts_to_legacy).

    Args:
        adv_setting: Строка AdvSetting для одной WB-кампании (adv_id).
        adv_data: ``adv.data`` из AuctionAdv/Adv.
    """
    bid_type_raw = adv_data.get("bidType")
    bid_type = str(bid_type_raw).lower() if bid_type_raw is not None else None
    auto_params = adv_data.get("autoParams") or {}
    active = auto_params.get("active") or {}
    adv_setting.wb_bid_type = bid_type
    adv_setting.wb_placement_search = bool(active.get("search"))
    adv_setting.wb_placement_recommendations = bool(active.get("recom"))


def wb_campaign_meta_known(adv: AdvSetting) -> bool:
    """True, если после sync известен bid_type."""
    return getattr(adv, "wb_bid_type", None) is not None


def wb_supports_normquery_minus_phrases(adv: AdvSetting) -> bool:
    """manual + search — требование WB для normquery set-minus/get-minus."""
    if not wb_campaign_meta_known(adv):
        return False
    return (
        getattr(adv, "wb_bid_type", None) == "manual"
        and getattr(adv, "wb_placement_search", None) is True
    )


def wb_is_manual_shelf_only(adv: AdvSetting) -> bool:
    """manual + поиск выключен + рекомендации включены (полочная авто-РК)."""
    if not wb_campaign_meta_known(adv):
        return False
    return (
        getattr(adv, "wb_bid_type", None) == "manual"
        and getattr(adv, "wb_placement_search", None) is False
        and getattr(adv, "wb_placement_recommendations", None) is True
    )
