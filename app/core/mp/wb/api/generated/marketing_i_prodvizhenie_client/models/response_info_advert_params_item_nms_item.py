from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseInfoAdvertParamsItemNmsItem")


@_attrs_define
class ResponseInfoAdvertParamsItemNmsItem:
    """
    Attributes:
        nm (Union[Unset, int]): Artikul WB
        active (Union[Unset, bool]): Sostojanie kartochki tovara:
              - `true` — aktivna
              - `false` — neaktivna
    """

    nm: Union[Unset, int] = UNSET
    active: Union[Unset, bool] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm = self.nm

        active = self.active

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm is not UNSET:
            field_dict["nm"] = nm
        if active is not UNSET:
            field_dict["active"] = active

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        nm = d.pop("nm", UNSET)

        active = d.pop("active", UNSET)

        response_info_advert_params_item_nms_item = cls(
            nm=nm,
            active=active,
        )

        response_info_advert_params_item_nms_item.additional_properties = d
        return response_info_advert_params_item_nms_item

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
