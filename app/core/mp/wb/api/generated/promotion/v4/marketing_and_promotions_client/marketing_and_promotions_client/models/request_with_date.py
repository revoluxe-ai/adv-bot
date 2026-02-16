import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="RequestWithDate")


@_attrs_define
class RequestWithDate:
    """
    Attributes:
        id (int): Campaign ID
        dates (List[datetime.date]): Dates for which information needs to be provided
    """

    id: int
    dates: List[datetime.date]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        dates = []
        for dates_item_data in self.dates:
            dates_item = dates_item_data.isoformat()
            dates.append(dates_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "dates": dates,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        id = d.pop("id")

        dates = []
        _dates = d.pop("dates")
        for dates_item_data in _dates:
            dates_item = isoparse(dates_item_data).date()

            dates.append(dates_item)

        request_with_date = cls(
            id=id,
            dates=dates,
        )

        request_with_date.additional_properties = d
        return request_with_date

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
