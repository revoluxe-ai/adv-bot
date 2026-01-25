from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.patch_api_advert_v1_bids_body_bids_item_nm_bids_item_placement import (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)

T = TypeVar("T", bound="PatchApiAdvertV1BidsBodyBidsItemNmBidsItem")


@_attrs_define
class PatchApiAdvertV1BidsBodyBidsItemNmBidsItem:
    """
    Attributes:
        nm_id (int): Artikul WB
        bid_kopecks (int): Stavka, kopejki
        placement (PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement): Mesto razmeschenija:
              - `search` — v poiske (dlja kampanij s ruchnoj stavkoj)
              - `recommendations`— v rekomendatsijah (dlja kampanij s ruchnoj stavkoj)
              - `combined` — v poiske i rekomendatsijah (dlja kampanij s edinoj stavkoj)
    """

    nm_id: int
    bid_kopecks: int
    placement: PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        bid_kopecks = self.bid_kopecks

        placement = self.placement.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nm_id": nm_id,
                "bid_kopecks": bid_kopecks,
                "placement": placement,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nm_id")

        bid_kopecks = d.pop("bid_kopecks")

        placement = PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement(
            d.pop("placement")
        )

        patch_api_advert_v1_bids_body_bids_item_nm_bids_item = cls(
            nm_id=nm_id,
            bid_kopecks=bid_kopecks,
            placement=placement,
        )

        patch_api_advert_v1_bids_body_bids_item_nm_bids_item.additional_properties = d
        return patch_api_advert_v1_bids_body_bids_item_nm_bids_item

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
