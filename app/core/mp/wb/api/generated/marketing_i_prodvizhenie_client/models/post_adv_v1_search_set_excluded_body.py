from typing import Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1SearchSetExcludedBody")


@_attrs_define
class PostAdvV1SearchSetExcludedBody:
    """
    Attributes:
        excluded (Union[Unset, List[str]]): Spisok minus-fraz, do 1000 fraz
    """

    excluded: Union[Unset, List[str]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        excluded: Union[Unset, List[str]] = UNSET
        if not isinstance(self.excluded, Unset):
            excluded = self.excluded

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if excluded is not UNSET:
            field_dict["excluded"] = excluded

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        excluded = cast(List[str], d.pop("excluded", UNSET))

        post_adv_v1_search_set_excluded_body = cls(
            excluded=excluded,
        )

        post_adv_v1_search_set_excluded_body.additional_properties = d
        return post_adv_v1_search_set_excluded_body

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
