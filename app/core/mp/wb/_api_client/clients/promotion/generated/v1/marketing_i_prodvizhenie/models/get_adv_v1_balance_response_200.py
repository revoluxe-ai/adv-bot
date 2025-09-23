from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_balance_response_200_cashbacks_item import (
        GetAdvV1BalanceResponse200CashbacksItem,
    )


T = TypeVar("T", bound="GetAdvV1BalanceResponse200")


@_attrs_define
class GetAdvV1BalanceResponse200:
    """
    Attributes:
        balance (Union[Unset, int]): Schet, rublej
        net (Union[Unset, int]): Balans, rublej
        bonus (Union[Unset, int]): Bonusy, rublej
        cashbacks (Union[Unset, list['GetAdvV1BalanceResponse200CashbacksItem']]): Promo-bonusy
    """

    balance: Union[Unset, int] = UNSET
    net: Union[Unset, int] = UNSET
    bonus: Union[Unset, int] = UNSET
    cashbacks: Union[Unset, list["GetAdvV1BalanceResponse200CashbacksItem"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        balance = self.balance

        net = self.net

        bonus = self.bonus

        cashbacks: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.cashbacks, Unset):
            cashbacks = []
            for cashbacks_item_data in self.cashbacks:
                cashbacks_item = cashbacks_item_data.to_dict()
                cashbacks.append(cashbacks_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if balance is not UNSET:
            field_dict["balance"] = balance
        if net is not UNSET:
            field_dict["net"] = net
        if bonus is not UNSET:
            field_dict["bonus"] = bonus
        if cashbacks is not UNSET:
            field_dict["cashbacks"] = cashbacks

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_balance_response_200_cashbacks_item import (
            GetAdvV1BalanceResponse200CashbacksItem,
        )

        d = dict(src_dict)
        balance = d.pop("balance", UNSET)

        net = d.pop("net", UNSET)

        bonus = d.pop("bonus", UNSET)

        cashbacks = []
        _cashbacks = d.pop("cashbacks", UNSET)
        for cashbacks_item_data in _cashbacks or []:
            cashbacks_item = GetAdvV1BalanceResponse200CashbacksItem.from_dict(
                cashbacks_item_data
            )

            cashbacks.append(cashbacks_item)

        get_adv_v1_balance_response_200 = cls(
            balance=balance,
            net=net,
            bonus=bonus,
            cashbacks=cashbacks,
        )

        get_adv_v1_balance_response_200.additional_properties = d
        return get_adv_v1_balance_response_200

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
