from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="BrandsResponseBrandsItem")


@_attrs_define
class BrandsResponseBrandsItem:
    """
    Attributes:
        id (int): ID brenda Example: 9007199254.
        logo_url (str): URL logotipa brenda
        name (str): Nazvanie brenda Example: Brand.
    """

    id: int
    logo_url: str
    name: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        logo_url = self.logo_url

        name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "logoUrl": logo_url,
                "name": name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        logo_url = d.pop("logoUrl")

        name = d.pop("name")

        brands_response_brands_item = cls(
            id=id,
            logo_url=logo_url,
            name=name,
        )

        brands_response_brands_item.additional_properties = d
        return brands_response_brands_item

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
