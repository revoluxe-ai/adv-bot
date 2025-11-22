import datetime
from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

T = TypeVar("T", bound="NmReportGroupedHistoryResponseDataItemHistoryItem")


@_attrs_define
class NmReportGroupedHistoryResponseDataItemHistoryItem:
    """
    Attributes:
        dt (Union[Unset, datetime.date]): Data Example: 2023-06-21.
        open_card_count (Union[Unset, int]): Kolichestvo perehodov v kartochku tovara
        add_to_cart_count (Union[Unset, int]): Polozhili v korzinu, shtuk
        orders_count (Union[Unset, int]): Zakazali tovarov, sht
        orders_sum_rub (Union[Unset, int]): Zakazali na summu, rub.
        buyouts_count (Union[Unset, int]): Vykupili tovarov, sht.
        buyouts_sum_rub (Union[Unset, int]): Vykupili na summu, rub.
        buyout_percent (Union[Unset, int]): Protsent vykupa, % (Kakoj protsent posetitelej, zakazavshih tovar, ego
            vykupili. Bez ucheta tovarov, kotorye esche dostavljajutsja pokupatelju.)
        add_to_cart_conversion (Union[Unset, int]): Konversija v korzinu, % (Kakoj protsent posetitelej, otkryvshih
            kartochku tovara, dobavili tovar v korzinu)
        cart_to_order_conversion (Union[Unset, int]): Konversija v zakaz, % (Kakoj protsent posetitelej, dobavivshih
            tovar v korzinu, sdelali zakaz)
    """

    dt: Union[Unset, datetime.date] = UNSET
    open_card_count: Union[Unset, int] = UNSET
    add_to_cart_count: Union[Unset, int] = UNSET
    orders_count: Union[Unset, int] = UNSET
    orders_sum_rub: Union[Unset, int] = UNSET
    buyouts_count: Union[Unset, int] = UNSET
    buyouts_sum_rub: Union[Unset, int] = UNSET
    buyout_percent: Union[Unset, int] = UNSET
    add_to_cart_conversion: Union[Unset, int] = UNSET
    cart_to_order_conversion: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        dt: Union[Unset, str] = UNSET
        if not isinstance(self.dt, Unset):
            dt = self.dt.isoformat()

        open_card_count = self.open_card_count

        add_to_cart_count = self.add_to_cart_count

        orders_count = self.orders_count

        orders_sum_rub = self.orders_sum_rub

        buyouts_count = self.buyouts_count

        buyouts_sum_rub = self.buyouts_sum_rub

        buyout_percent = self.buyout_percent

        add_to_cart_conversion = self.add_to_cart_conversion

        cart_to_order_conversion = self.cart_to_order_conversion

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if dt is not UNSET:
            field_dict["dt"] = dt
        if open_card_count is not UNSET:
            field_dict["openCardCount"] = open_card_count
        if add_to_cart_count is not UNSET:
            field_dict["addToCartCount"] = add_to_cart_count
        if orders_count is not UNSET:
            field_dict["ordersCount"] = orders_count
        if orders_sum_rub is not UNSET:
            field_dict["ordersSumRub"] = orders_sum_rub
        if buyouts_count is not UNSET:
            field_dict["buyoutsCount"] = buyouts_count
        if buyouts_sum_rub is not UNSET:
            field_dict["buyoutsSumRub"] = buyouts_sum_rub
        if buyout_percent is not UNSET:
            field_dict["buyoutPercent"] = buyout_percent
        if add_to_cart_conversion is not UNSET:
            field_dict["addToCartConversion"] = add_to_cart_conversion
        if cart_to_order_conversion is not UNSET:
            field_dict["cartToOrderConversion"] = cart_to_order_conversion

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        _dt = d.pop("dt", UNSET)
        dt: Union[Unset, datetime.date]
        if isinstance(_dt, Unset):
            dt = UNSET
        else:
            dt = isoparse(_dt).date()

        open_card_count = d.pop("openCardCount", UNSET)

        add_to_cart_count = d.pop("addToCartCount", UNSET)

        orders_count = d.pop("ordersCount", UNSET)

        orders_sum_rub = d.pop("ordersSumRub", UNSET)

        buyouts_count = d.pop("buyoutsCount", UNSET)

        buyouts_sum_rub = d.pop("buyoutsSumRub", UNSET)

        buyout_percent = d.pop("buyoutPercent", UNSET)

        add_to_cart_conversion = d.pop("addToCartConversion", UNSET)

        cart_to_order_conversion = d.pop("cartToOrderConversion", UNSET)

        nm_report_grouped_history_response_data_item_history_item = cls(
            dt=dt,
            open_card_count=open_card_count,
            add_to_cart_count=add_to_cart_count,
            orders_count=orders_count,
            orders_sum_rub=orders_sum_rub,
            buyouts_count=buyouts_count,
            buyouts_sum_rub=buyouts_sum_rub,
            buyout_percent=buyout_percent,
            add_to_cart_conversion=add_to_cart_conversion,
            cart_to_order_conversion=cart_to_order_conversion,
        )

        nm_report_grouped_history_response_data_item_history_item.additional_properties = d
        return nm_report_grouped_history_response_data_item_history_item

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
