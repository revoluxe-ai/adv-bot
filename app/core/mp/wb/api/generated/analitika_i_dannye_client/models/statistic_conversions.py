from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="StatisticConversions")


@_attrs_define
class StatisticConversions:
    """
    Attributes:
        add_to_cart_percent (int): Konversija v korzinu. Kakoj protsent posetitelej, otkryvshih kartochku tovara,
            dobavili tovar v korzinu, % Example: 19.
        cart_to_order_percent (int): Konversija v zakaz. Kakoj protsent posetitelej, dobavivshih tovar v korzinu,
            sdelali zakaz, % Example: 65.
        buyout_percent (int): Protsent vykupa. Kakoj protsent posetitelej, zakazavshih tovar, ego vykupili. Bez ucheta
            tovarov, kotorye esche dostavljajutsja pokupatelju, %
    """

    add_to_cart_percent: int
    cart_to_order_percent: int
    buyout_percent: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        add_to_cart_percent = self.add_to_cart_percent

        cart_to_order_percent = self.cart_to_order_percent

        buyout_percent = self.buyout_percent

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "addToCartPercent": add_to_cart_percent,
                "cartToOrderPercent": cart_to_order_percent,
                "buyoutPercent": buyout_percent,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        add_to_cart_percent = d.pop("addToCartPercent")

        cart_to_order_percent = d.pop("cartToOrderPercent")

        buyout_percent = d.pop("buyoutPercent")

        statistic_conversions = cls(
            add_to_cart_percent=add_to_cart_percent,
            cart_to_order_percent=cart_to_order_percent,
            buyout_percent=buyout_percent,
        )

        statistic_conversions.additional_properties = d
        return statistic_conversions

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
