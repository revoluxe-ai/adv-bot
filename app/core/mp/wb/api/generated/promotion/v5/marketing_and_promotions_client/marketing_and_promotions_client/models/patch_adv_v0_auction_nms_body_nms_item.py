from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.patch_adv_v0_auction_nms_body_nms_item_nms import (
        PatchAdvV0AuctionNmsBodyNmsItemNms,
    )


T = TypeVar("T", bound="PatchAdvV0AuctionNmsBodyNmsItem")


@_attrs_define
class PatchAdvV0AuctionNmsBodyNmsItem:
    """
    Attributes:
        advert_id (int): Campaign ID
        nms (PatchAdvV0AuctionNmsBodyNmsItemNms): Product cards. Maximum of 50 products per campaign
    """

    advert_id: int
    nms: "PatchAdvV0AuctionNmsBodyNmsItemNms"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        advert_id = self.advert_id

        nms = self.nms.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advert_id": advert_id,
                "nms": nms,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.patch_adv_v0_auction_nms_body_nms_item_nms import (
            PatchAdvV0AuctionNmsBodyNmsItemNms,
        )

        d = src_dict.copy()
        advert_id = d.pop("advert_id")

        nms = PatchAdvV0AuctionNmsBodyNmsItemNms.from_dict(d.pop("nms"))

        patch_adv_v0_auction_nms_body_nms_item = cls(
            advert_id=advert_id,
            nms=nms,
        )

        patch_adv_v0_auction_nms_body_nms_item.additional_properties = d
        return patch_adv_v0_auction_nms_body_nms_item

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
