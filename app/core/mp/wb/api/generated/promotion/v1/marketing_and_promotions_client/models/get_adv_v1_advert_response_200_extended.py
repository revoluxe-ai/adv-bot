from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1AdvertResponse200Extended")


@_attrs_define
class GetAdvV1AdvertResponse200Extended:
    """
    Attributes:
        reason (None | str | Unset): Moderator's remark
        expenses (int | Unset): Expenses
        from_ (datetime.datetime | Unset): Media campaign display start date and time
        to (datetime.datetime | Unset): Media campaign display end date and time
        updated_at (datetime.datetime | Unset): Campaign update date and time
        price (int | Unset): Cost of placement by day for type `1`
        budget (int | Unset): Budget balance for type `2`
        operation (int | Unset): Source of charge-off:
              - `1` — balance sheet
              - `2` — account
        contract_id (int | Unset): Contract ID, for contracted sellers
    """

    reason: None | str | Unset = UNSET
    expenses: int | Unset = UNSET
    from_: datetime.datetime | Unset = UNSET
    to: datetime.datetime | Unset = UNSET
    updated_at: datetime.datetime | Unset = UNSET
    price: int | Unset = UNSET
    budget: int | Unset = UNSET
    operation: int | Unset = UNSET
    contract_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        reason: None | str | Unset
        if isinstance(self.reason, Unset):
            reason = UNSET
        else:
            reason = self.reason

        expenses = self.expenses

        from_: str | Unset = UNSET
        if not isinstance(self.from_, Unset):
            from_ = self.from_.isoformat()

        to: str | Unset = UNSET
        if not isinstance(self.to, Unset):
            to = self.to.isoformat()

        updated_at: str | Unset = UNSET
        if not isinstance(self.updated_at, Unset):
            updated_at = self.updated_at.isoformat()

        price = self.price

        budget = self.budget

        operation = self.operation

        contract_id = self.contract_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if reason is not UNSET:
            field_dict["reason"] = reason
        if expenses is not UNSET:
            field_dict["expenses"] = expenses
        if from_ is not UNSET:
            field_dict["from"] = from_
        if to is not UNSET:
            field_dict["to"] = to
        if updated_at is not UNSET:
            field_dict["updated_at"] = updated_at
        if price is not UNSET:
            field_dict["price"] = price
        if budget is not UNSET:
            field_dict["budget"] = budget
        if operation is not UNSET:
            field_dict["operation"] = operation
        if contract_id is not UNSET:
            field_dict["contract_id"] = contract_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_reason(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        reason = _parse_reason(d.pop("reason", UNSET))

        expenses = d.pop("expenses", UNSET)

        _from_ = d.pop("from", UNSET)
        from_: datetime.datetime | Unset
        if isinstance(_from_, Unset):
            from_ = UNSET
        else:
            from_ = isoparse(_from_)

        _to = d.pop("to", UNSET)
        to: datetime.datetime | Unset
        if isinstance(_to, Unset):
            to = UNSET
        else:
            to = isoparse(_to)

        _updated_at = d.pop("updated_at", UNSET)
        updated_at: datetime.datetime | Unset
        if isinstance(_updated_at, Unset):
            updated_at = UNSET
        else:
            updated_at = isoparse(_updated_at)

        price = d.pop("price", UNSET)

        budget = d.pop("budget", UNSET)

        operation = d.pop("operation", UNSET)

        contract_id = d.pop("contract_id", UNSET)

        get_adv_v1_advert_response_200_extended = cls(
            reason=reason,
            expenses=expenses,
            from_=from_,
            to=to,
            updated_at=updated_at,
            price=price,
            budget=budget,
            operation=operation,
            contract_id=contract_id,
        )

        get_adv_v1_advert_response_200_extended.additional_properties = d
        return get_adv_v1_advert_response_200_extended

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
