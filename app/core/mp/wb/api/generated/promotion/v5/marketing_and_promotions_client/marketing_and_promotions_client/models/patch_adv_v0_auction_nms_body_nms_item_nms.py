from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PatchAdvV0AuctionNmsBodyNmsItemNms")


@_attrs_define
class PatchAdvV0AuctionNmsBodyNmsItemNms:
    """Product cards. Maximum of 50 products per campaign

    Attributes:
        add (Union[Unset, Any]): The product cards that need to be added
        delete (Union[Unset, List[int]]): The product cards that need to be deleted
    """

    add: Union[Unset, Any] = UNSET
    delete: Union[Unset, List[int]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        add = self.add

        delete: Union[Unset, List[int]] = UNSET
        if not isinstance(self.delete, Unset):
            delete = self.delete

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if add is not UNSET:
            field_dict["add"] = add
        if delete is not UNSET:
            field_dict["delete"] = delete

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        add = d.pop("add", UNSET)

        delete = cast(List[int], d.pop("delete", UNSET))

        patch_adv_v0_auction_nms_body_nms_item_nms = cls(
            add=add,
            delete=delete,
        )

        patch_adv_v0_auction_nms_body_nms_item_nms.additional_properties = d
        return patch_adv_v0_auction_nms_body_nms_item_nms

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
