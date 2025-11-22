import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="VisibilityInfoByMonthItem")


@_attrs_define
class VisibilityInfoByMonthItem:
    """
    Attributes:
        dt (datetime.date): Data Example: 2024-02-10.
        visibility (int): Vidimost' kartochki v rezul'tatah poiska, % Example: 100.
        open_ (int): Kolichestvo perehodov v kartochku Example: 124.
    """

    dt: datetime.date
    visibility: int
    open_: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        dt = self.dt.isoformat()

        visibility = self.visibility

        open_ = self.open_

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "dt": dt,
                "visibility": visibility,
                "open": open_,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        dt = isoparse(d.pop("dt")).date()

        visibility = d.pop("visibility")

        open_ = d.pop("open")

        visibility_info_by_month_item = cls(
            dt=dt,
            visibility=visibility,
            open_=open_,
        )

        visibility_info_by_month_item.additional_properties = d
        return visibility_info_by_month_item

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
