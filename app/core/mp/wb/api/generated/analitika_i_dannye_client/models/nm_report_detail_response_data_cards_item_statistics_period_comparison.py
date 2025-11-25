from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_response_data_cards_item_statistics_period_comparison_conversions import (
        NmReportDetailResponseDataCardsItemStatisticsPeriodComparisonConversions,
    )


T = TypeVar("T", bound="NmReportDetailResponseDataCardsItemStatisticsPeriodComparison")


@_attrs_define
class NmReportDetailResponseDataCardsItemStatisticsPeriodComparison:
    """Sravnenie dvuh periodov, v protsentah

    Attributes:
        open_card_dynamics (Union[Unset, int]): Dinamika perehodov v kartochku tovara
        add_to_cart_dynamics (Union[Unset, int]): Dinamika dobavlenij v korzinu
        orders_count_dynamics (Union[Unset, int]): Dinamika kolichestva zakazov Example: -100.
        orders_sum_rub_dynamics (Union[Unset, int]): Dinamika summy zakazov, rublej Example: -100.
        buyouts_count_dynamics (Union[Unset, int]): Dinamika vykupov, shtuk Example: -100.
        buyouts_sum_rub_dynamics (Union[Unset, int]): Dinamika summy vykupov, rublej Example: -100.
        cancel_count_dynamics (Union[Unset, int]): Dinamika otmen tovarov, shtuk
        cancel_sum_rub_dynamics (Union[Unset, int]): Dinamika summ otmen tovarov, rublej
        avg_orders_count_per_day_dynamics (Union[Unset, int]): Dinamika srednego kolichestva zakazov v den'
        avg_price_rub_dynamics (Union[Unset, int]): Dinamika srednej tseny na tovary. Uchityvajutsja skidki dlja aktsij
            i WB skidka. Example: -100.
        conversions (Union[Unset, NmReportDetailResponseDataCardsItemStatisticsPeriodComparisonConversions]): Konversii
    """

    open_card_dynamics: Union[Unset, int] = UNSET
    add_to_cart_dynamics: Union[Unset, int] = UNSET
    orders_count_dynamics: Union[Unset, int] = UNSET
    orders_sum_rub_dynamics: Union[Unset, int] = UNSET
    buyouts_count_dynamics: Union[Unset, int] = UNSET
    buyouts_sum_rub_dynamics: Union[Unset, int] = UNSET
    cancel_count_dynamics: Union[Unset, int] = UNSET
    cancel_sum_rub_dynamics: Union[Unset, int] = UNSET
    avg_orders_count_per_day_dynamics: Union[Unset, int] = UNSET
    avg_price_rub_dynamics: Union[Unset, int] = UNSET
    conversions: Union[Unset, "NmReportDetailResponseDataCardsItemStatisticsPeriodComparisonConversions"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        open_card_dynamics = self.open_card_dynamics

        add_to_cart_dynamics = self.add_to_cart_dynamics

        orders_count_dynamics = self.orders_count_dynamics

        orders_sum_rub_dynamics = self.orders_sum_rub_dynamics

        buyouts_count_dynamics = self.buyouts_count_dynamics

        buyouts_sum_rub_dynamics = self.buyouts_sum_rub_dynamics

        cancel_count_dynamics = self.cancel_count_dynamics

        cancel_sum_rub_dynamics = self.cancel_sum_rub_dynamics

        avg_orders_count_per_day_dynamics = self.avg_orders_count_per_day_dynamics

        avg_price_rub_dynamics = self.avg_price_rub_dynamics

        conversions: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.conversions, Unset):
            conversions = self.conversions.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if open_card_dynamics is not UNSET:
            field_dict["openCardDynamics"] = open_card_dynamics
        if add_to_cart_dynamics is not UNSET:
            field_dict["addToCartDynamics"] = add_to_cart_dynamics
        if orders_count_dynamics is not UNSET:
            field_dict["ordersCountDynamics"] = orders_count_dynamics
        if orders_sum_rub_dynamics is not UNSET:
            field_dict["ordersSumRubDynamics"] = orders_sum_rub_dynamics
        if buyouts_count_dynamics is not UNSET:
            field_dict["buyoutsCountDynamics"] = buyouts_count_dynamics
        if buyouts_sum_rub_dynamics is not UNSET:
            field_dict["buyoutsSumRubDynamics"] = buyouts_sum_rub_dynamics
        if cancel_count_dynamics is not UNSET:
            field_dict["cancelCountDynamics"] = cancel_count_dynamics
        if cancel_sum_rub_dynamics is not UNSET:
            field_dict["cancelSumRubDynamics"] = cancel_sum_rub_dynamics
        if avg_orders_count_per_day_dynamics is not UNSET:
            field_dict["avgOrdersCountPerDayDynamics"] = avg_orders_count_per_day_dynamics
        if avg_price_rub_dynamics is not UNSET:
            field_dict["avgPriceRubDynamics"] = avg_price_rub_dynamics
        if conversions is not UNSET:
            field_dict["conversions"] = conversions

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_response_data_cards_item_statistics_period_comparison_conversions import (
            NmReportDetailResponseDataCardsItemStatisticsPeriodComparisonConversions,
        )

        d = src_dict.copy()
        open_card_dynamics = d.pop("openCardDynamics", UNSET)

        add_to_cart_dynamics = d.pop("addToCartDynamics", UNSET)

        orders_count_dynamics = d.pop("ordersCountDynamics", UNSET)

        orders_sum_rub_dynamics = d.pop("ordersSumRubDynamics", UNSET)

        buyouts_count_dynamics = d.pop("buyoutsCountDynamics", UNSET)

        buyouts_sum_rub_dynamics = d.pop("buyoutsSumRubDynamics", UNSET)

        cancel_count_dynamics = d.pop("cancelCountDynamics", UNSET)

        cancel_sum_rub_dynamics = d.pop("cancelSumRubDynamics", UNSET)

        avg_orders_count_per_day_dynamics = d.pop("avgOrdersCountPerDayDynamics", UNSET)

        avg_price_rub_dynamics = d.pop("avgPriceRubDynamics", UNSET)

        _conversions = d.pop("conversions", UNSET)
        conversions: Union[Unset, NmReportDetailResponseDataCardsItemStatisticsPeriodComparisonConversions]
        if isinstance(_conversions, Unset):
            conversions = UNSET
        else:
            conversions = NmReportDetailResponseDataCardsItemStatisticsPeriodComparisonConversions.from_dict(
                _conversions
            )

        nm_report_detail_response_data_cards_item_statistics_period_comparison = cls(
            open_card_dynamics=open_card_dynamics,
            add_to_cart_dynamics=add_to_cart_dynamics,
            orders_count_dynamics=orders_count_dynamics,
            orders_sum_rub_dynamics=orders_sum_rub_dynamics,
            buyouts_count_dynamics=buyouts_count_dynamics,
            buyouts_sum_rub_dynamics=buyouts_sum_rub_dynamics,
            cancel_count_dynamics=cancel_count_dynamics,
            cancel_sum_rub_dynamics=cancel_sum_rub_dynamics,
            avg_orders_count_per_day_dynamics=avg_orders_count_per_day_dynamics,
            avg_price_rub_dynamics=avg_price_rub_dynamics,
            conversions=conversions,
        )

        nm_report_detail_response_data_cards_item_statistics_period_comparison.additional_properties = d
        return nm_report_detail_response_data_cards_item_statistics_period_comparison

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
