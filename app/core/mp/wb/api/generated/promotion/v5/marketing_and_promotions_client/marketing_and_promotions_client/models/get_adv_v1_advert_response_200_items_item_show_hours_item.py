from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1AdvertResponse200ItemsItemShowHoursItem")


@_attrs_define
class GetAdvV1AdvertResponse200ItemsItemShowHoursItem:
    """
    Attributes:
        from_ (Union[Unset, int]): Start time
        to (Union[Unset, int]): End time
    """

    from_: Union[Unset, int] = UNSET
    to: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from_ = self.from_

        to = self.to

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if from_ is not UNSET:
            field_dict["From"] = from_
        if to is not UNSET:
            field_dict["To"] = to

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        from_ = d.pop("From", UNSET)

        to = d.pop("To", UNSET)

        get_adv_v1_advert_response_200_items_item_show_hours_item = cls(
            from_=from_,
            to=to,
        )

        get_adv_v1_advert_response_200_items_item_show_hours_item.additional_properties = d
        return get_adv_v1_advert_response_200_items_item_show_hours_item

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
