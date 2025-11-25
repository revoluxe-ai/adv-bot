import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="History")


@_attrs_define
class History:
    """
    Attributes:
        date (datetime.date): Data sbora statistiki Example: 2024-10-23.
        open_count (int): Kolichestvo perehodov v kartochku tovara Example: 45.
        cart_count (int): Polozhili v korzinu, sht. Example: 34.
        order_count (int): Zakazali tovarov, sht. Example: 19.
        order_sum (int): Zakazali na summu Example: 1262.
        buyout_count (int): Vykupili tovarov, sht. Example: 19.
        buyout_sum (int): Vykupili na summu Example: 1262.
        buyout_percent (int): Protsent vykupa Example: 35.
        add_to_cart_conversion (int): Protsent vykupa Example: 43.
        cart_to_order_conversion (int): Konversija v zakaz. Kakoj protsent posetitelej, dobavivshih tovar v korzinu,
            sdelali zakaz
        add_to_wishlist_count (int): Kolichestvo dobavlenij tovara v **Otlozhennye**
    """

    date: datetime.date
    open_count: int
    cart_count: int
    order_count: int
    order_sum: int
    buyout_count: int
    buyout_sum: int
    buyout_percent: int
    add_to_cart_conversion: int
    cart_to_order_conversion: int
    add_to_wishlist_count: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        date = self.date.isoformat()

        open_count = self.open_count

        cart_count = self.cart_count

        order_count = self.order_count

        order_sum = self.order_sum

        buyout_count = self.buyout_count

        buyout_sum = self.buyout_sum

        buyout_percent = self.buyout_percent

        add_to_cart_conversion = self.add_to_cart_conversion

        cart_to_order_conversion = self.cart_to_order_conversion

        add_to_wishlist_count = self.add_to_wishlist_count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "date": date,
                "openCount": open_count,
                "cartCount": cart_count,
                "orderCount": order_count,
                "orderSum": order_sum,
                "buyoutCount": buyout_count,
                "buyoutSum": buyout_sum,
                "buyoutPercent": buyout_percent,
                "addToCartConversion": add_to_cart_conversion,
                "cartToOrderConversion": cart_to_order_conversion,
                "addToWishlistCount": add_to_wishlist_count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        date = isoparse(d.pop("date")).date()

        open_count = d.pop("openCount")

        cart_count = d.pop("cartCount")

        order_count = d.pop("orderCount")

        order_sum = d.pop("orderSum")

        buyout_count = d.pop("buyoutCount")

        buyout_sum = d.pop("buyoutSum")

        buyout_percent = d.pop("buyoutPercent")

        add_to_cart_conversion = d.pop("addToCartConversion")

        cart_to_order_conversion = d.pop("cartToOrderConversion")

        add_to_wishlist_count = d.pop("addToWishlistCount")

        history = cls(
            date=date,
            open_count=open_count,
            cart_count=cart_count,
            order_count=order_count,
            order_sum=order_sum,
            buyout_count=buyout_count,
            buyout_sum=buyout_sum,
            buyout_percent=buyout_percent,
            add_to_cart_conversion=add_to_cart_conversion,
            cart_to_order_conversion=cart_to_order_conversion,
            add_to_wishlist_count=add_to_wishlist_count,
        )

        history.additional_properties = d
        return history

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
