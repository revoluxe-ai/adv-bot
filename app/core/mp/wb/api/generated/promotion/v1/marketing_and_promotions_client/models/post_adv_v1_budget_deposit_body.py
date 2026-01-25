from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1BudgetDepositBody")


@_attrs_define
class PostAdvV1BudgetDepositBody:
    """
    Attributes:
        sum_ (int | Unset): Budget top-up amount Example: 5000.
        cashback_sum (int | Unset): Top-up budget sum paid with promo bonuses.
            <br>
            You can top up only a certain percentage of the amount, indicated in the `percent` field of the response from
            the method for getting [balance](./promotion#tag/Finance/paths/~1adv~1v1~1balance/get).
            <br>
            Promo bonuses are only applicable to these top-up sources:
              - `0` — account
              - `1` — balance sheet
             Example: 1000.
        cashback_percent (int | Unset): The percentage of the top-up amount that can be paid with promo bonuses. You
            need to specify the value of the `percent` field from the response for the method for getting [balance]
            <br>
            If you specified `cashback_sum`, the `cashback_percent` parameter becomes required
             Example: 50.
        type_ (int | Unset): Type of top-up source:
            - `0` — Account
            - `1` — Balance
            - `3` — Bonuses
             Example: 1.
        return_ (bool | Unset): Response return flag (`true` means updated campaign budget size will be returned in the
            response, `false` or empty means nothing will be returned).
    """

    sum_: int | Unset = UNSET
    cashback_sum: int | Unset = UNSET
    cashback_percent: int | Unset = UNSET
    type_: int | Unset = UNSET
    return_: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sum_ = self.sum_

        cashback_sum = self.cashback_sum

        cashback_percent = self.cashback_percent

        type_ = self.type_

        return_ = self.return_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if sum_ is not UNSET:
            field_dict["sum"] = sum_
        if cashback_sum is not UNSET:
            field_dict["cashback_sum"] = cashback_sum
        if cashback_percent is not UNSET:
            field_dict["cashback_percent"] = cashback_percent
        if type_ is not UNSET:
            field_dict["type"] = type_
        if return_ is not UNSET:
            field_dict["return"] = return_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sum_ = d.pop("sum", UNSET)

        cashback_sum = d.pop("cashback_sum", UNSET)

        cashback_percent = d.pop("cashback_percent", UNSET)

        type_ = d.pop("type", UNSET)

        return_ = d.pop("return", UNSET)

        post_adv_v1_budget_deposit_body = cls(
            sum_=sum_,
            cashback_sum=cashback_sum,
            cashback_percent=cashback_percent,
            type_=type_,
            return_=return_,
        )

        post_adv_v1_budget_deposit_body.additional_properties = d
        return post_adv_v1_budget_deposit_body

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
