from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_api_v3_dbw_warehouses_warehouse_id_contacts_response_200_contacts_item import (
        GetApiV3DbwWarehousesWarehouseIdContactsResponse200ContactsItem,
    )


T = TypeVar("T", bound="GetApiV3DbwWarehousesWarehouseIdContactsResponse200")


@_attrs_define
class GetApiV3DbwWarehousesWarehouseIdContactsResponse200:
    """Spisok kontaktov sklada prodavtsa

    Attributes:
        contacts (list[GetApiV3DbwWarehousesWarehouseIdContactsResponse200ContactsItem] | Unset):
    """

    contacts: (
        list[GetApiV3DbwWarehousesWarehouseIdContactsResponse200ContactsItem] | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        contacts: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.contacts, Unset):
            contacts = []
            for contacts_item_data in self.contacts:
                contacts_item = contacts_item_data.to_dict()
                contacts.append(contacts_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if contacts is not UNSET:
            field_dict["contacts"] = contacts

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_api_v3_dbw_warehouses_warehouse_id_contacts_response_200_contacts_item import (
            GetApiV3DbwWarehousesWarehouseIdContactsResponse200ContactsItem,
        )

        d = dict(src_dict)
        _contacts = d.pop("contacts", UNSET)
        contacts: (
            list[GetApiV3DbwWarehousesWarehouseIdContactsResponse200ContactsItem]
            | Unset
        ) = UNSET
        if _contacts is not UNSET:
            contacts = []
            for contacts_item_data in _contacts:
                contacts_item = GetApiV3DbwWarehousesWarehouseIdContactsResponse200ContactsItem.from_dict(
                    contacts_item_data
                )

                contacts.append(contacts_item)

        get_api_v3_dbw_warehouses_warehouse_id_contacts_response_200 = cls(
            contacts=contacts,
        )

        get_api_v3_dbw_warehouses_warehouse_id_contacts_response_200.additional_properties = d
        return get_api_v3_dbw_warehouses_warehouse_id_contacts_response_200

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
