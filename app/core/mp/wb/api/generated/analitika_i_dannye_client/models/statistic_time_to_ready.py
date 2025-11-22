from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="StatisticTimeToReady")


@_attrs_define
class StatisticTimeToReady:
    """
    Attributes:
        days (int): Dni Example: 1.
        hours (int): Chasy Example: 8.
        mins (int): Minuty Example: 34.
    """

    days: int
    hours: int
    mins: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        days = self.days

        hours = self.hours

        mins = self.mins

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "days": days,
                "hours": hours,
                "mins": mins,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        days = d.pop("days")

        hours = d.pop("hours")

        mins = d.pop("mins")

        statistic_time_to_ready = cls(
            days=days,
            hours=hours,
            mins=mins,
        )

        statistic_time_to_ready.additional_properties = d
        return statistic_time_to_ready

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
