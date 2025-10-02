from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1AutoUpdatenmBody")


@_attrs_define
class PostAdvV1AutoUpdatenmBody:
    """
    Attributes:
        add (Union[Unset, list[int]]): Kartochki tovarov, kotorye neobhodimo dobavit'
        delete (Union[Unset, list[int]]): Kartochki tovarov, kotorye neobhodimo udalit'
    """

    add: Union[Unset, list[int]] = UNSET
    delete: Union[Unset, list[int]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        add: Union[Unset, list[int]] = UNSET
        if not isinstance(self.add, Unset):
            add = self.add

        delete: Union[Unset, list[int]] = UNSET
        if not isinstance(self.delete, Unset):
            delete = self.delete

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if add is not UNSET:
            field_dict["add"] = add
        if delete is not UNSET:
            field_dict["delete"] = delete

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        add = cast(list[int], d.pop("add", UNSET))

        delete = cast(list[int], d.pop("delete", UNSET))

        post_adv_v1_auto_updatenm_body = cls(
            add=add,
            delete=delete,
        )

        post_adv_v1_auto_updatenm_body.additional_properties = d
        return post_adv_v1_auto_updatenm_body

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
