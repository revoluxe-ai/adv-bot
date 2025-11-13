from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.request_with_interval_interval import RequestWithIntervalInterval


T = TypeVar("T", bound="RequestWithInterval")


@_attrs_define
class RequestWithInterval:
    """
    Attributes:
        id (int): ID kampanii
        interval (RequestWithIntervalInterval): Vremennoj diapazon, za kotoryj neobhodimo vydat' dannye
    """

    id: int
    interval: "RequestWithIntervalInterval"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        id = self.id

        interval = self.interval.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "interval": interval,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.request_with_interval_interval import RequestWithIntervalInterval

        d = src_dict.copy()
        id = d.pop("id")

        interval = RequestWithIntervalInterval.from_dict(d.pop("interval"))

        request_with_interval = cls(
            id=id,
            interval=interval,
        )

        request_with_interval.additional_properties = d
        return request_with_interval

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
