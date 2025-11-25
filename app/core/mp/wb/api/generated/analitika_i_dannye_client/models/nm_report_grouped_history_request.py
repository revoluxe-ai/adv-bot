from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_grouped_history_request_period import NmReportGroupedHistoryRequestPeriod


T = TypeVar("T", bound="NmReportGroupedHistoryRequest")


@_attrs_define
class NmReportGroupedHistoryRequest:
    """
    Attributes:
        period (NmReportGroupedHistoryRequestPeriod): Period
        object_i_ds (Union[Unset, List[int]]): ID predmetov
        brand_names (Union[Unset, List[str]]): Brendy
        tag_i_ds (Union[Unset, List[int]]): ID jarlykov
        timezone (Union[Unset, str]): Vremennaja zona.<br> Esli ne ukazano, to po umolchaniju ispol'zuetsja
            Europe/Moscow.
             Example: Europe/Moscow.
        aggregation_level (Union[Unset, str]): Tip agregatsii. Esli ne ukazano, to po umolchaniju ispol'zuetsja
            agregatsija po dnjam. <br> Dostupnye urovni agregatsii `day`, `week`
             Example: day.
    """

    period: "NmReportGroupedHistoryRequestPeriod"
    object_i_ds: Union[Unset, List[int]] = UNSET
    brand_names: Union[Unset, List[str]] = UNSET
    tag_i_ds: Union[Unset, List[int]] = UNSET
    timezone: Union[Unset, str] = UNSET
    aggregation_level: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        period = self.period.to_dict()

        object_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.object_i_ds, Unset):
            object_i_ds = self.object_i_ds

        brand_names: Union[Unset, List[str]] = UNSET
        if not isinstance(self.brand_names, Unset):
            brand_names = self.brand_names

        tag_i_ds: Union[Unset, List[int]] = UNSET
        if not isinstance(self.tag_i_ds, Unset):
            tag_i_ds = self.tag_i_ds

        timezone = self.timezone

        aggregation_level = self.aggregation_level

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "period": period,
            }
        )
        if object_i_ds is not UNSET:
            field_dict["objectIDs"] = object_i_ds
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if tag_i_ds is not UNSET:
            field_dict["tagIDs"] = tag_i_ds
        if timezone is not UNSET:
            field_dict["timezone"] = timezone
        if aggregation_level is not UNSET:
            field_dict["aggregationLevel"] = aggregation_level

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_grouped_history_request_period import NmReportGroupedHistoryRequestPeriod

        d = src_dict.copy()
        period = NmReportGroupedHistoryRequestPeriod.from_dict(d.pop("period"))

        object_i_ds = cast(List[int], d.pop("objectIDs", UNSET))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        tag_i_ds = cast(List[int], d.pop("tagIDs", UNSET))

        timezone = d.pop("timezone", UNSET)

        aggregation_level = d.pop("aggregationLevel", UNSET)

        nm_report_grouped_history_request = cls(
            period=period,
            object_i_ds=object_i_ds,
            brand_names=brand_names,
            tag_i_ds=tag_i_ds,
            timezone=timezone,
            aggregation_level=aggregation_level,
        )

        nm_report_grouped_history_request.additional_properties = d
        return nm_report_grouped_history_request

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
