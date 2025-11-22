from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_response_data_cards_item_statistics_selected_period_conversions import (
        NmReportDetailResponseDataCardsItemStatisticsSelectedPeriodConversions,
    )


T = TypeVar("T", bound="NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod")


@_attrs_define
class NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod:
    """Zaprashivaemyj period

    Attributes:
        begin (Union[Unset, str]): Nachalo perioda Example: 2023-06-01 20:05:32.
        end (Union[Unset, str]): Konets perioda Example: 2024-03-01 20:05:32.
        open_card_count (Union[Unset, int]): Kolichestvo perehodov v kartochku tovara
        add_to_cart_count (Union[Unset, int]): Polozhili v korzinu, shtuk
        orders_count (Union[Unset, int]): Zakazali tovarov, sht
        orders_sum_rub (Union[Unset, int]): Zakazali na summu, rub.
        buyouts_count (Union[Unset, int]): Vykupili tovarov, sht.
        buyouts_sum_rub (Union[Unset, int]): Vykupili na summu, rub.
        cancel_count (Union[Unset, int]): Otmenili tovarov, sht.
        cancel_sum_rub (Union[Unset, int]): Otmenili na summu, rub.
        avg_price_rub (Union[Unset, int]): Srednjaja tsena, rub.
        avg_orders_count_per_day (Union[Unset, int]): Srednee kolichestvo zakazov v den', sht.
        conversions (Union[Unset, NmReportDetailResponseDataCardsItemStatisticsSelectedPeriodConversions]): Konversii
    """

    begin: Union[Unset, str] = UNSET
    end: Union[Unset, str] = UNSET
    open_card_count: Union[Unset, int] = UNSET
    add_to_cart_count: Union[Unset, int] = UNSET
    orders_count: Union[Unset, int] = UNSET
    orders_sum_rub: Union[Unset, int] = UNSET
    buyouts_count: Union[Unset, int] = UNSET
    buyouts_sum_rub: Union[Unset, int] = UNSET
    cancel_count: Union[Unset, int] = UNSET
    cancel_sum_rub: Union[Unset, int] = UNSET
    avg_price_rub: Union[Unset, int] = UNSET
    avg_orders_count_per_day: Union[Unset, int] = UNSET
    conversions: Union[Unset, "NmReportDetailResponseDataCardsItemStatisticsSelectedPeriodConversions"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        begin = self.begin

        end = self.end

        open_card_count = self.open_card_count

        add_to_cart_count = self.add_to_cart_count

        orders_count = self.orders_count

        orders_sum_rub = self.orders_sum_rub

        buyouts_count = self.buyouts_count

        buyouts_sum_rub = self.buyouts_sum_rub

        cancel_count = self.cancel_count

        cancel_sum_rub = self.cancel_sum_rub

        avg_price_rub = self.avg_price_rub

        avg_orders_count_per_day = self.avg_orders_count_per_day

        conversions: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.conversions, Unset):
            conversions = self.conversions.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if begin is not UNSET:
            field_dict["begin"] = begin
        if end is not UNSET:
            field_dict["end"] = end
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
        if cancel_count is not UNSET:
            field_dict["cancelCount"] = cancel_count
        if cancel_sum_rub is not UNSET:
            field_dict["cancelSumRub"] = cancel_sum_rub
        if avg_price_rub is not UNSET:
            field_dict["avgPriceRub"] = avg_price_rub
        if avg_orders_count_per_day is not UNSET:
            field_dict["avgOrdersCountPerDay"] = avg_orders_count_per_day
        if conversions is not UNSET:
            field_dict["conversions"] = conversions

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_response_data_cards_item_statistics_selected_period_conversions import (
            NmReportDetailResponseDataCardsItemStatisticsSelectedPeriodConversions,
        )

        d = src_dict.copy()
        begin = d.pop("begin", UNSET)

        end = d.pop("end", UNSET)

        open_card_count = d.pop("openCardCount", UNSET)

        add_to_cart_count = d.pop("addToCartCount", UNSET)

        orders_count = d.pop("ordersCount", UNSET)

        orders_sum_rub = d.pop("ordersSumRub", UNSET)

        buyouts_count = d.pop("buyoutsCount", UNSET)

        buyouts_sum_rub = d.pop("buyoutsSumRub", UNSET)

        cancel_count = d.pop("cancelCount", UNSET)

        cancel_sum_rub = d.pop("cancelSumRub", UNSET)

        avg_price_rub = d.pop("avgPriceRub", UNSET)

        avg_orders_count_per_day = d.pop("avgOrdersCountPerDay", UNSET)

        _conversions = d.pop("conversions", UNSET)
        conversions: Union[Unset, NmReportDetailResponseDataCardsItemStatisticsSelectedPeriodConversions]
        if isinstance(_conversions, Unset):
            conversions = UNSET
        else:
            conversions = NmReportDetailResponseDataCardsItemStatisticsSelectedPeriodConversions.from_dict(_conversions)

        nm_report_detail_response_data_cards_item_statistics_selected_period = cls(
            begin=begin,
            end=end,
            open_card_count=open_card_count,
            add_to_cart_count=add_to_cart_count,
            orders_count=orders_count,
            orders_sum_rub=orders_sum_rub,
            buyouts_count=buyouts_count,
            buyouts_sum_rub=buyouts_sum_rub,
            cancel_count=cancel_count,
            cancel_sum_rub=cancel_sum_rub,
            avg_price_rub=avg_price_rub,
            avg_orders_count_per_day=avg_orders_count_per_day,
            conversions=conversions,
        )

        nm_report_detail_response_data_cards_item_statistics_selected_period.additional_properties = d
        return nm_report_detail_response_data_cards_item_statistics_selected_period

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
