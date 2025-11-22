from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NmReportDetailResponseDataCardsItemStatisticsPreviousPeriodConversions")


@_attrs_define
class NmReportDetailResponseDataCardsItemStatisticsPreviousPeriodConversions:
    """Konversii

    Attributes:
        add_to_cart_percent (Union[Unset, int]): Konversija v korzinu, % (Kakoj protsent posetitelej, otkryvshih
            kartochku tovara, dobavili tovar v korzinu)
        cart_to_order_percent (Union[Unset, int]): Konversija v zakaz, % (Kakoj protsent posetitelej, dobavivshih tovar
            v korzinu, sdelali zakaz)
        buyouts_percent (Union[Unset, int]): Protsent vykupa, % (Kakoj protsent posetitelej, zakazavshih tovar, ego
            vykupili. Bez ucheta tovarov, kotorye esche dostavljajutsja pokupatelju.) Example: 100.
    """

    add_to_cart_percent: Union[Unset, int] = UNSET
    cart_to_order_percent: Union[Unset, int] = UNSET
    buyouts_percent: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        add_to_cart_percent = self.add_to_cart_percent

        cart_to_order_percent = self.cart_to_order_percent

        buyouts_percent = self.buyouts_percent

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if add_to_cart_percent is not UNSET:
            field_dict["addToCartPercent"] = add_to_cart_percent
        if cart_to_order_percent is not UNSET:
            field_dict["cartToOrderPercent"] = cart_to_order_percent
        if buyouts_percent is not UNSET:
            field_dict["buyoutsPercent"] = buyouts_percent

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        add_to_cart_percent = d.pop("addToCartPercent", UNSET)

        cart_to_order_percent = d.pop("cartToOrderPercent", UNSET)

        buyouts_percent = d.pop("buyoutsPercent", UNSET)

        nm_report_detail_response_data_cards_item_statistics_previous_period_conversions = cls(
            add_to_cart_percent=add_to_cart_percent,
            cart_to_order_percent=cart_to_order_percent,
            buyouts_percent=buyouts_percent,
        )

        nm_report_detail_response_data_cards_item_statistics_previous_period_conversions.additional_properties = d
        return nm_report_detail_response_data_cards_item_statistics_previous_period_conversions

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
