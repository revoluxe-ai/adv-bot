from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="SearchReportPositionChartItem")


@_attrs_define
class SearchReportPositionChartItem:
    """
    Attributes:
        dt (str): Data Example: 2024-10-19.
        average (int): Srednjaja pozitsija tovara v rezul'tatah poiska Example: 1.
        median (int): Mediannaja pozitsija tovara v rezul'tatah poiska Example: 1.
    """

    dt: str
    average: int
    median: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        dt = self.dt

        average = self.average

        median = self.median

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "dt": dt,
                "average": average,
                "median": median,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        dt = d.pop("dt")

        average = d.pop("average")

        median = d.pop("median")

        search_report_position_chart_item = cls(
            dt=dt,
            average=average,
            median=median,
        )

        search_report_position_chart_item.additional_properties = d
        return search_report_position_chart_item

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
