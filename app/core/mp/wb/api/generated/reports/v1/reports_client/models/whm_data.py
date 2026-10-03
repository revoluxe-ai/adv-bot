from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.whm_data_reports_item import WHMDataReportsItem


T = TypeVar("T", bound="WHMData")


@_attrs_define
class WHMData:
    """Response data

    Attributes:
        reports (List['WHMDataReportsItem']): Measurements
        total (int): Number of measurements in the report. Except `limit` and `offset` Example: 11.
    """

    reports: List["WHMDataReportsItem"]
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
        from ..models.whm_data_reports_item import WHMDataReportsItem

        d = src_dict.copy()
        reports = []
        _reports = d.pop("reports")
        for reports_item_data in _reports:
            reports_item = WHMDataReportsItem.from_dict(reports_item_data)

            reports.append(reports_item)

        total = d.pop("total")

        whm_data = cls(
            reports=reports,
            total=total,
        )

        whm_data.additional_properties = d
        return whm_data

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
