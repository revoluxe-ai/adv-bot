from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1BudgetDepositBody")


@_attrs_define
class PostAdvV1BudgetDepositBody:
    """
    Attributes:
        sum_ (int | Unset): Obschaja summa popolnenija bjudzheta Example: 5000.
        cashback_sum (int | None | Unset): Summa popolnenija bjudzheta promo-bonusami.
            <br>
            Popolnit' mozhno tol'ko opredelennyj protsent ot obschej summy, ukazannyj v pole `percent` otveta metoda
            poluchenija [balansa](./promotion#tag/Finansy/paths/~1adv~1v1~1balance/get).
            <br>
            Ostavshajasja chast' obschej summy spishetsja s ukazannogo istochnika popolnenija.
            Popolnit' mozhno tol'ko opredelennyj protsent ot obschej summy, ukazannyj v pole `percent` otveta metoda
            poluchenija [balansa](./promotion#tag/Finansy/paths/~1adv~1v1~1balance/get).
            <br>
            Ostavshajasja chast' obschej summy spishetsja s ukazannogo istochnika popolnenija.
            <br>
            Spisat' promo-bonusy mozhno tol'ko dlja istochnikov popolnenija:
              - `0` — schet
              - `1` — balans
             Example: 1000.
        cashback_percent (int | None | Unset): Protsent ot summy popolnenija, kotoryj mozhno popolnit' promo-bonusami.
            Nuzhno ukazat' znachenie polja percent iz otveta metoda poluchenija
            [balansa](./promotion#tag/Finansy/paths/~1adv~1v1~1balance/get)
            <br>
            Esli vy ukazali `cashback_sum`, parametr `cashback_percent` stanovitsja objazatel'nym
             Example: 50.
        type_ (int | Unset): Tip istochnika popolnenija:
            - `0` — Schet
            - `1` — Balans
            - `3` — Bonusy
             Example: 1.
        return_ (bool | Unset): Flag vozvrata otveta (`true` — v otvete vernetsja obnovlennyj razmer bjudzheta kampanii,
            `false` ili ne ukazat' parametr voobsche — ne vernetsja.)
    """

    sum_: int | Unset = UNSET
    cashback_sum: int | None | Unset = UNSET
    cashback_percent: int | None | Unset = UNSET
    type_: int | Unset = UNSET
    return_: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sum_ = self.sum_

        cashback_sum: int | None | Unset
        if isinstance(self.cashback_sum, Unset):
            cashback_sum = UNSET
        else:
            cashback_sum = self.cashback_sum

        cashback_percent: int | None | Unset
        if isinstance(self.cashback_percent, Unset):
            cashback_percent = UNSET
        else:
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

        def _parse_cashback_sum(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        cashback_sum = _parse_cashback_sum(d.pop("cashback_sum", UNSET))

        def _parse_cashback_percent(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        cashback_percent = _parse_cashback_percent(d.pop("cashback_percent", UNSET))

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
