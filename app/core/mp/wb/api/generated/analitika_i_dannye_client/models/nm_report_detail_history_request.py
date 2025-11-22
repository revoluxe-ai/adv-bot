from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_history_request_period import NmReportDetailHistoryRequestPeriod


T = TypeVar("T", bound="NmReportDetailHistoryRequest")


@_attrs_define
class NmReportDetailHistoryRequest:
    """
    Attributes:
        nm_i_ds (List[int]): Artikul WB (maksimum 20)
        period (NmReportDetailHistoryRequestPeriod): Period
        timezone (Union[Unset, str]): Vremennaja zona.<br> Esli ne ukazano, to po umolchaniju ispol'zuetsja
            Europe/Moscow.
             Example: Europe/Moscow.
        aggregation_level (Union[Unset, str]): Tip agregatsii. Esli ne ukazano, to po umolchaniju ispol'zuetsja
            agregatsija po dnjam. <br> Dostupnye urovni agregatsii `day`, `week`
             Example: day.
    """

    nm_i_ds: List[int]
    period: "NmReportDetailHistoryRequestPeriod"
    timezone: Union[Unset, str] = UNSET
    aggregation_level: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_i_ds = self.nm_i_ds

        period = self.period.to_dict()

        timezone = self.timezone

        aggregation_level = self.aggregation_level

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmIDs": nm_i_ds,
                "period": period,
            }
        )
        if timezone is not UNSET:
            field_dict["timezone"] = timezone
        if aggregation_level is not UNSET:
            field_dict["aggregationLevel"] = aggregation_level

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_history_request_period import NmReportDetailHistoryRequestPeriod

        d = src_dict.copy()
        nm_i_ds = cast(List[int], d.pop("nmIDs"))

        period = NmReportDetailHistoryRequestPeriod.from_dict(d.pop("period"))

        timezone = d.pop("timezone", UNSET)

        aggregation_level = d.pop("aggregationLevel", UNSET)

        nm_report_detail_history_request = cls(
            nm_i_ds=nm_i_ds,
            period=period,
            timezone=timezone,
            aggregation_level=aggregation_level,
        )

        nm_report_detail_history_request.additional_properties = d
        return nm_report_detail_history_request

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
