from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1PaymentsResponse200Item")


@_attrs_define
class GetAdvV1PaymentsResponse200Item:
    """
    Attributes:
        id (Union[Unset, int]): ID platezha
        date (Union[Unset, str]): Data platezha
        sum_ (Union[Unset, int]): Summa platezha
        type_ (Union[Unset, int]): <dl>
            <dt>Tip istochnika spisanija:</dt>
            <dd><code>0</code> — Schet</dd>
            <dd><code>1</code> — Balans</dd>
            <dd><code>3</code> — Kartoj</dd>
            </dl>
        status_id (Union[Unset, int]): <dl>
            <dt>Status:</dt>
            <dd><code>0</code> — oshibka</dd>
            <dd><code>1</code> — obrabotano</dd>
            </dl>
        card_status (Union[Unset, str]): <dl>
            <dt>Status operatsii(pri oplate kartoj):</dt>
            <dd><b>success</b> — uspeh</dd>
            <dd><b>fail</b> — neuspeh</dd>
            <dd><b>pending</b> — v ozhidanii otveta</dd>
            <dd><b>unknown</b> — neizvestno</dd>
            </dl>
    """

    id: Union[Unset, int] = UNSET
    date: Union[Unset, str] = UNSET
    sum_: Union[Unset, int] = UNSET
    type_: Union[Unset, int] = UNSET
    status_id: Union[Unset, int] = UNSET
    card_status: Union[Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        date = self.date

        sum_ = self.sum_

        type_ = self.type_

        status_id = self.status_id

        card_status = self.card_status

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if date is not UNSET:
            field_dict["date"] = date
        if sum_ is not UNSET:
            field_dict["sum"] = sum_
        if type_ is not UNSET:
            field_dict["type"] = type_
        if status_id is not UNSET:
            field_dict["statusId"] = status_id
        if card_status is not UNSET:
            field_dict["cardStatus"] = card_status

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        date = d.pop("date", UNSET)

        sum_ = d.pop("sum", UNSET)

        type_ = d.pop("type", UNSET)

        status_id = d.pop("statusId", UNSET)

        card_status = d.pop("cardStatus", UNSET)

        get_adv_v1_payments_response_200_item = cls(
            id=id,
            date=date,
            sum_=sum_,
            type_=type_,
            status_id=status_id,
            card_status=card_status,
        )

        get_adv_v1_payments_response_200_item.additional_properties = d
        return get_adv_v1_payments_response_200_item

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
