from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.patch_adv_v0_auction_nms_response_200_nms_item_nms import (
        PatchAdvV0AuctionNmsResponse200NmsItemNms,
    )


T = TypeVar("T", bound="PatchAdvV0AuctionNmsResponse200NmsItem")


@_attrs_define
class PatchAdvV0AuctionNmsResponse200NmsItem:
    """
    Attributes:
        advert_id (int): ID kampanii
        nms (PatchAdvV0AuctionNmsResponse200NmsItemNms): Kartochki tovarov
    """

    advert_id: int
    nms: PatchAdvV0AuctionNmsResponse200NmsItemNms
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        nms = self.nms.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nms": nms,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.patch_adv_v0_auction_nms_response_200_nms_item_nms import (
            PatchAdvV0AuctionNmsResponse200NmsItemNms,
        )

        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        nms = PatchAdvV0AuctionNmsResponse200NmsItemNms.from_dict(d.pop("nms"))

        patch_adv_v0_auction_nms_response_200_nms_item = cls(
            advert_id=advert_id,
            nms=nms,
        )

        patch_adv_v0_auction_nms_response_200_nms_item.additional_properties = d
        return patch_adv_v0_auction_nms_response_200_nms_item

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
