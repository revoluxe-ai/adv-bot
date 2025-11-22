import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="PeriodOrdersRequest")


@_attrs_define
class PeriodOrdersRequest:
    """Tekuschij period. Maksimum 7 sutok

    Attributes:
        start (datetime.date): Data nachala perioda. Ne pozdnee `end`. Ne ranee 365 sutok ot segodnja Example:
            2024-02-10.
        end (datetime.date): Data okonchanija perioda. Ne ranee 365 sutok ot segodnja Example: 2024-02-10.
    """

    start: datetime.date
    end: datetime.date
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        start = self.start.isoformat()

        end = self.end.isoformat()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "start": start,
                "end": end,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        start = isoparse(d.pop("start")).date()

        end = isoparse(d.pop("end")).date()

        period_orders_request = cls(
            start=start,
            end=end,
        )

        period_orders_request.additional_properties = d
        return period_orders_request

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
