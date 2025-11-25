from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="TableCommonMetricsAvgStockTurnover")


@_attrs_define
class TableCommonMetricsAvgStockTurnover:
    """Oborachivaemost' srednih ostatkov. Osobye sluchai:
    1. `"hours":-1` — beskonechnaja dlitel'nost'
    2. `"hours":-2` — nulevaja dlitel'nost'
    3. `"hours":-3` — nerasschitannaja dlitel'nost'

      Attributes:
          days (int): Kolichestvo dnej Example: 5.
          hours (int): Kolichestvo chasov Example: 15.
    """

    days: int
    hours: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        days = self.days

        hours = self.hours

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "days": days,
                "hours": hours,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        days = d.pop("days")

        hours = d.pop("hours")

        table_common_metrics_avg_stock_turnover = cls(
            days=days,
            hours=hours,
        )

        table_common_metrics_avg_stock_turnover.additional_properties = d
        return table_common_metrics_avg_stock_turnover

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
