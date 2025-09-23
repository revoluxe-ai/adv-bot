from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1BalanceResponse200CashbacksItem")


@_attrs_define
class GetAdvV1BalanceResponse200CashbacksItem:
    """
    Attributes:
        sum_ (Union[Unset, int]): Promo-bonusy, ₽
        percent (Union[Unset, int]): Protsent ot summy popolnenija bjudzheta kampanii, kotoryj mozhno oplatit' promo-
            bonusami za odin raz
        expiration_date (Union[Unset, str]): Data okonchanija dejstvija promo-bonusov
    """

    sum_: Union[Unset, int] = UNSET
    percent: Union[Unset, int] = UNSET
    expiration_date: Union[Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sum_ = self.sum_

        percent = self.percent

        expiration_date = self.expiration_date

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if sum_ is not UNSET:
            field_dict["sum"] = sum_
        if percent is not UNSET:
            field_dict["percent"] = percent
        if expiration_date is not UNSET:
            field_dict["expiration_date"] = expiration_date

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        sum_ = d.pop("sum", UNSET)

        percent = d.pop("percent", UNSET)

        expiration_date = d.pop("expiration_date", UNSET)

        get_adv_v1_balance_response_200_cashbacks_item = cls(
            sum_=sum_,
            percent=percent,
            expiration_date=expiration_date,
        )

        get_adv_v1_balance_response_200_cashbacks_item.additional_properties = d
        return get_adv_v1_balance_response_200_cashbacks_item

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
