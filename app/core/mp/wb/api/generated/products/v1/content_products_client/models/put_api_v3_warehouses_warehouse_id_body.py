from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PutApiV3WarehousesWarehouseIdBody")


@_attrs_define
class PutApiV3WarehousesWarehouseIdBody:
    """
    Attributes:
        name (str): Imja sklada prodavtsa Example: Sklad Koledino.
        office_id (int): ID sklada WB Example: 15.
    """

    name: str
    office_id: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        office_id = self.office_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
                "officeId": office_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        office_id = d.pop("officeId")

        put_api_v3_warehouses_warehouse_id_body = cls(
            name=name,
            office_id=office_id,
        )

        put_api_v3_warehouses_warehouse_id_body.additional_properties = d
        return put_api_v3_warehouses_warehouse_id_body

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
