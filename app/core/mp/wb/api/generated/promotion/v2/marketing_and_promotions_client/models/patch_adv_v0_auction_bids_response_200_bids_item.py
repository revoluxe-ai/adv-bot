from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.patch_adv_v0_auction_bids_response_200_bids_item_nm_bids_item import (
        PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem,
    )


T = TypeVar("T", bound="PatchAdvV0AuctionBidsResponse200BidsItem")


@_attrs_define
class PatchAdvV0AuctionBidsResponse200BidsItem:
    """
    Attributes:
        advert_id (int): ID kampanii
        nm_bids (list[PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem]): Stavki
    """

    advert_id: int
    nm_bids: list[PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        nm_bids = []
        for nm_bids_item_data in self.nm_bids:
            nm_bids_item = nm_bids_item_data.to_dict()
            nm_bids.append(nm_bids_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nm_bids": nm_bids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.patch_adv_v0_auction_bids_response_200_bids_item_nm_bids_item import (
            PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem,
        )

        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        nm_bids = []
        _nm_bids = d.pop("nm_bids")
        for nm_bids_item_data in _nm_bids:
            nm_bids_item = PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem.from_dict(
                nm_bids_item_data
            )

            nm_bids.append(nm_bids_item)

        patch_adv_v0_auction_bids_response_200_bids_item = cls(
            advert_id=advert_id,
            nm_bids=nm_bids,
        )

        patch_adv_v0_auction_bids_response_200_bids_item.additional_properties = d
        return patch_adv_v0_auction_bids_response_200_bids_item

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
