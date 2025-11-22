from typing import Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PatchAdvV0AuctionNmsResponse200NmsItemNms")


@_attrs_define
class PatchAdvV0AuctionNmsResponse200NmsItemNms:
    """Kartochki tovarov

    Attributes:
        added (List[int]): Dobavlennye kartochki tovarov
        deleted (List[int]): Udalennye kartochki tovarov
    """

    added: List[int]
    deleted: List[int]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        added = self.added

        deleted = self.deleted

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "added": added,
                "deleted": deleted,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        added = cast(List[int], d.pop("added"))

        deleted = cast(List[int], d.pop("deleted"))

        patch_adv_v0_auction_nms_response_200_nms_item_nms = cls(
            added=added,
            deleted=deleted,
        )

        patch_adv_v0_auction_nms_response_200_nms_item_nms.additional_properties = d
        return patch_adv_v0_auction_nms_response_200_nms_item_nms

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
