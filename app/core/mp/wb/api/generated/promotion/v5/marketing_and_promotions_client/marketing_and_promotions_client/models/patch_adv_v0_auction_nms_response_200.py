from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.patch_adv_v0_auction_nms_response_200_nms_item import (
        PatchAdvV0AuctionNmsResponse200NmsItem,
    )


T = TypeVar("T", bound="PatchAdvV0AuctionNmsResponse200")


@_attrs_define
class PatchAdvV0AuctionNmsResponse200:
    """
    Attributes:
        nms (List['PatchAdvV0AuctionNmsResponse200NmsItem']): The result of processing the request
    """

    nms: List["PatchAdvV0AuctionNmsResponse200NmsItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nms = []
        for nms_item_data in self.nms:
            nms_item = nms_item_data.to_dict()
            nms.append(nms_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nms": nms,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.patch_adv_v0_auction_nms_response_200_nms_item import (
            PatchAdvV0AuctionNmsResponse200NmsItem,
        )

        d = src_dict.copy()
        nms = []
        _nms = d.pop("nms")
        for nms_item_data in _nms:
            nms_item = PatchAdvV0AuctionNmsResponse200NmsItem.from_dict(nms_item_data)

            nms.append(nms_item)

        patch_adv_v0_auction_nms_response_200 = cls(
            nms=nms,
        )

        patch_adv_v0_auction_nms_response_200.additional_properties = d
        return patch_adv_v0_auction_nms_response_200

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
