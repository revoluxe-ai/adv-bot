from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="TaskCreatedData")


@_attrs_define
class TaskCreatedData:
    """Dannye otveta

    Attributes:
        id (int | Unset): ID zagruzki
        already_exists (bool | Unset): Flag dublirovanija zagruzki: `true` — takaja zagruzka uzhe est'
    """

    id: int | Unset = UNSET
    already_exists: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        already_exists = self.already_exists

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if already_exists is not UNSET:
            field_dict["alreadyExists"] = already_exists

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        already_exists = d.pop("alreadyExists", UNSET)

        task_created_data = cls(
            id=id,
            already_exists=already_exists,
        )

        task_created_data.additional_properties = d
        return task_created_data

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
