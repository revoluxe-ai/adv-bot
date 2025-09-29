from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PromotionsGoodsList")


@_attrs_define
class PromotionsGoodsList:
    """
    Attributes:
        id (Union[Unset, int]): ID kartochki tovara Example: 162579635.
        in_action (Union[Unset, bool]): Uchastvuet v aktsii:
              - `true` — da
              - `false` — net
             Example: True.
        price (Union[Unset, float]): Tekuschaja roznichnaja tsena Example: 1500.
        currency_code (Union[Unset, str]): Valjuta v formate ISO 4217 Example: RUB.
        plan_price (Union[Unset, float]): Planovaja tsena (tsena vo vremja aktsii) Example: 1000.
        discount (Union[Unset, int]): Tekuschaja skidka Example: 15.
        plan_discount (Union[Unset, int]): Rekomenduemaja skidka dlja uchastija v aktsii Example: 34.
    """

    id: Union[Unset, int] = UNSET
    in_action: Union[Unset, bool] = UNSET
    price: Union[Unset, float] = UNSET
    currency_code: Union[Unset, str] = UNSET
    plan_price: Union[Unset, float] = UNSET
    discount: Union[Unset, int] = UNSET
    plan_discount: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        in_action = self.in_action

        price = self.price

        currency_code = self.currency_code

        plan_price = self.plan_price

        discount = self.discount

        plan_discount = self.plan_discount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if in_action is not UNSET:
            field_dict["inAction"] = in_action
        if price is not UNSET:
            field_dict["price"] = price
        if currency_code is not UNSET:
            field_dict["currencyCode"] = currency_code
        if plan_price is not UNSET:
            field_dict["planPrice"] = plan_price
        if discount is not UNSET:
            field_dict["discount"] = discount
        if plan_discount is not UNSET:
            field_dict["planDiscount"] = plan_discount

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id", UNSET)

        in_action = d.pop("inAction", UNSET)

        price = d.pop("price", UNSET)

        currency_code = d.pop("currencyCode", UNSET)

        plan_price = d.pop("planPrice", UNSET)

        discount = d.pop("discount", UNSET)

        plan_discount = d.pop("planDiscount", UNSET)

        promotions_goods_list = cls(
            id=id,
            in_action=in_action,
            price=price,
            currency_code=currency_code,
            plan_price=plan_price,
            discount=discount,
            plan_discount=plan_discount,
        )

        promotions_goods_list.additional_properties = d
        return promotions_goods_list

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
