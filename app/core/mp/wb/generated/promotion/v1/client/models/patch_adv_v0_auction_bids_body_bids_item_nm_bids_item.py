from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.patch_adv_v0_auction_bids_body_bids_item_nm_bids_item_placement import (
    PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement,
)

T = TypeVar("T", bound="PatchAdvV0AuctionBidsBodyBidsItemNmBidsItem")


@_attrs_define
class PatchAdvV0AuctionBidsBodyBidsItemNmBidsItem:
    """
    Attributes:
        nm_id (int): Artikul WB
        bid (int): Stavka
        placement (PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement): Mesto razmeschenija:
              - `search` — v poiske
              - `recommendations`— v rekomendatsijah
    """

    nm_id: int
    bid: int
    placement: PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        bid = self.bid

        placement = self.placement.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nm_id": nm_id,
                "bid": bid,
                "placement": placement,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nm_id")

        bid = d.pop("bid")

        placement = PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement(
            d.pop("placement")
        )

        patch_adv_v0_auction_bids_body_bids_item_nm_bids_item = cls(
            nm_id=nm_id,
            bid=bid,
            placement=placement,
        )

        patch_adv_v0_auction_bids_body_bids_item_nm_bids_item.additional_properties = d
        return patch_adv_v0_auction_bids_body_bids_item_nm_bids_item

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
