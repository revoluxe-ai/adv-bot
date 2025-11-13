from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1SearchSetPlusBody")


@_attrs_define
class PostAdvV1SearchSetPlusBody:
    """
    Attributes:
        pluse (Union[Unset, List[str]]): Spisok fiksirovannyh fraz (max. 100)
    """

    pluse: Union[Unset, List[str]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        pluse: Union[Unset, List[str]] = UNSET
        if not isinstance(self.pluse, Unset):
            pluse = self.pluse

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if pluse is not UNSET:
            field_dict["pluse"] = pluse

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        pluse = cast(List[str], d.pop("pluse", UNSET))

        post_adv_v1_search_set_plus_body = cls(
            pluse=pluse,
        )

        post_adv_v1_search_set_plus_body.additional_properties = d
        return post_adv_v1_search_set_plus_body

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
