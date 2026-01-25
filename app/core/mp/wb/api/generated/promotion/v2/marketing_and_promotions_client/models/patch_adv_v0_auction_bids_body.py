from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.patch_adv_v0_auction_bids_body_bids_item import (
        PatchAdvV0AuctionBidsBodyBidsItem,
    )


T = TypeVar("T", bound="PatchAdvV0AuctionBidsBody")


@_attrs_define
class PatchAdvV0AuctionBidsBody:
    """
    Attributes:
        bids (list[PatchAdvV0AuctionBidsBodyBidsItem]): Stavki v kampanijah
    """

    bids: list[PatchAdvV0AuctionBidsBodyBidsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bids = []
        for bids_item_data in self.bids:
            bids_item = bids_item_data.to_dict()
            bids.append(bids_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bids": bids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.patch_adv_v0_auction_bids_body_bids_item import (
            PatchAdvV0AuctionBidsBodyBidsItem,
        )

        d = dict(src_dict)
        bids = []
        _bids = d.pop("bids")
        for bids_item_data in _bids:
            bids_item = PatchAdvV0AuctionBidsBodyBidsItem.from_dict(bids_item_data)

            bids.append(bids_item)

        patch_adv_v0_auction_bids_body = cls(
            bids=bids,
        )

        patch_adv_v0_auction_bids_body.additional_properties = d
        return patch_adv_v0_auction_bids_body

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
