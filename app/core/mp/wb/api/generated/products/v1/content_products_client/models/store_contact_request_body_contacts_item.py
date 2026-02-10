from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="StoreContactRequestBodyContactsItem")


@_attrs_define
class StoreContactRequestBodyContactsItem:
    """
    Attributes:
        comment (str | Unset): Kommentarij Example: Ivanov Ivan Ivanovich. Zvonit' s 10 do 21 chasa..
        phone (str | Unset): Nomer telefona.<br>Podderzhivajutsja kody stran:
              - `+7` — Rossija, Kazahstan
              - `+374` — Armenija
              - `+375` — Belarus'
              - `+996` — Kyrgyzstan
             Example: +79998887766.
    """

    comment: str | Unset = UNSET
    phone: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        comment = self.comment

        phone = self.phone

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if comment is not UNSET:
            field_dict["comment"] = comment
        if phone is not UNSET:
            field_dict["phone"] = phone

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        comment = d.pop("comment", UNSET)

        phone = d.pop("phone", UNSET)

        store_contact_request_body_contacts_item = cls(
            comment=comment,
            phone=phone,
        )

        store_contact_request_body_contacts_item.additional_properties = d
        return store_contact_request_body_contacts_item

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
