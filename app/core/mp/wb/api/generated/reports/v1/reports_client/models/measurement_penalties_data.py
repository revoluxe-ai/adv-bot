from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.measurement_penalties_data_reports_item import (
        MeasurementPenaltiesDataReportsItem,
    )


T = TypeVar("T", bound="MeasurementPenaltiesData")


@_attrs_define
class MeasurementPenaltiesData:
    """Response data

    Attributes:
        reports (List['MeasurementPenaltiesDataReportsItem']): Retentions
        total (int): Number of retentions in the report. Except `limit` and `offset` Example: 11.
    """

    reports: List["MeasurementPenaltiesDataReportsItem"]
    total: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        reports = []
        for reports_item_data in self.reports:
            reports_item = reports_item_data.to_dict()
            reports.append(reports_item)

        total = self.total

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "reports": reports,
                "total": total,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.measurement_penalties_data_reports_item import (
            MeasurementPenaltiesDataReportsItem,
        )

        d = src_dict.copy()
        reports = []
        _reports = d.pop("reports")
        for reports_item_data in _reports:
            reports_item = MeasurementPenaltiesDataReportsItem.from_dict(
                reports_item_data
            )

            reports.append(reports_item)

        total = d.pop("total")

        measurement_penalties_data = cls(
            reports=reports,
            total=total,
        )

        measurement_penalties_data.additional_properties = d
        return measurement_penalties_data

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
