from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_response_data_cards_item_statistics_period_comparison import (
        NmReportDetailResponseDataCardsItemStatisticsPeriodComparison,
    )
    from ..models.nm_report_detail_response_data_cards_item_statistics_previous_period import (
        NmReportDetailResponseDataCardsItemStatisticsPreviousPeriod,
    )
    from ..models.nm_report_detail_response_data_cards_item_statistics_selected_period import (
        NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod,
    )


T = TypeVar("T", bound="NmReportDetailResponseDataCardsItemStatistics")


@_attrs_define
class NmReportDetailResponseDataCardsItemStatistics:
    """Statistika

    Attributes:
        selected_period (Union[Unset, NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod]): Zaprashivaemyj
            period
        previous_period (Union[Unset, NmReportDetailResponseDataCardsItemStatisticsPreviousPeriod]): Statistika za
            predyduschij period
        period_comparison (Union[Unset, NmReportDetailResponseDataCardsItemStatisticsPeriodComparison]): Sravnenie dvuh
            periodov, v protsentah
    """

    selected_period: Union[Unset, "NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod"] = UNSET
    previous_period: Union[Unset, "NmReportDetailResponseDataCardsItemStatisticsPreviousPeriod"] = UNSET
    period_comparison: Union[Unset, "NmReportDetailResponseDataCardsItemStatisticsPeriodComparison"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        selected_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.selected_period, Unset):
            selected_period = self.selected_period.to_dict()

        previous_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.previous_period, Unset):
            previous_period = self.previous_period.to_dict()

        period_comparison: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.period_comparison, Unset):
            period_comparison = self.period_comparison.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if selected_period is not UNSET:
            field_dict["selectedPeriod"] = selected_period
        if previous_period is not UNSET:
            field_dict["previousPeriod"] = previous_period
        if period_comparison is not UNSET:
            field_dict["periodComparison"] = period_comparison

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_response_data_cards_item_statistics_period_comparison import (
            NmReportDetailResponseDataCardsItemStatisticsPeriodComparison,
        )
        from ..models.nm_report_detail_response_data_cards_item_statistics_previous_period import (
            NmReportDetailResponseDataCardsItemStatisticsPreviousPeriod,
        )
        from ..models.nm_report_detail_response_data_cards_item_statistics_selected_period import (
            NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod,
        )

        d = src_dict.copy()
        _selected_period = d.pop("selectedPeriod", UNSET)
        selected_period: Union[Unset, NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod]
        if isinstance(_selected_period, Unset):
            selected_period = UNSET
        else:
            selected_period = NmReportDetailResponseDataCardsItemStatisticsSelectedPeriod.from_dict(_selected_period)

        _previous_period = d.pop("previousPeriod", UNSET)
        previous_period: Union[Unset, NmReportDetailResponseDataCardsItemStatisticsPreviousPeriod]
        if isinstance(_previous_period, Unset):
            previous_period = UNSET
        else:
            previous_period = NmReportDetailResponseDataCardsItemStatisticsPreviousPeriod.from_dict(_previous_period)

        _period_comparison = d.pop("periodComparison", UNSET)
        period_comparison: Union[Unset, NmReportDetailResponseDataCardsItemStatisticsPeriodComparison]
        if isinstance(_period_comparison, Unset):
            period_comparison = UNSET
        else:
            period_comparison = NmReportDetailResponseDataCardsItemStatisticsPeriodComparison.from_dict(
                _period_comparison
            )

        nm_report_detail_response_data_cards_item_statistics = cls(
            selected_period=selected_period,
            previous_period=previous_period,
            period_comparison=period_comparison,
        )

        nm_report_detail_response_data_cards_item_statistics.additional_properties = d
        return nm_report_detail_response_data_cards_item_statistics

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
