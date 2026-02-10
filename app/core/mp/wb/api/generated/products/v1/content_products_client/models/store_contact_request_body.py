from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.store_contact_request_body_contacts_item import (
        StoreContactRequestBodyContactsItem,
    )


T = TypeVar("T", bound="StoreContactRequestBody")


@_attrs_define
class StoreContactRequestBody:
    """Kontakty sklada prodavtsa

    Attributes:
        contacts (list[StoreContactRequestBodyContactsItem] | Unset):
    """

    contacts: list[StoreContactRequestBodyContactsItem] | Unset = UNSET
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
        from ..models.store_contact_request_body_contacts_item import (
            StoreContactRequestBodyContactsItem,
        )

        d = dict(src_dict)
        _contacts = d.pop("contacts", UNSET)
        contacts: list[StoreContactRequestBodyContactsItem] | Unset = UNSET
        if _contacts is not UNSET:
            contacts = []
            for contacts_item_data in _contacts:
                contacts_item = StoreContactRequestBodyContactsItem.from_dict(
                    contacts_item_data
                )

                contacts.append(contacts_item)

        store_contact_request_body = cls(
            contacts=contacts,
        )

        store_contact_request_body.additional_properties = d
        return store_contact_request_body

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
