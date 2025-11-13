from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="FullStatsError")


@_attrs_define
class FullStatsError:
    """Oshibka

    Attributes:
        detail (str): Detali oshibki
        origin (str): ID vnutrennego servisa WB
        request_id (str): ID zaprosa
        status (int): HTTP status-kod
        title (str): Zagolovok oshibki
    """

    detail: str
    origin: str
    request_id: str
    status: int
    title: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        detail = self.detail

        origin = self.origin

        request_id = self.request_id

        status = self.status

        title = self.title

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "detail": detail,
                "origin": origin,
                "request_id": request_id,
                "status": status,
                "title": title,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        detail = d.pop("detail")

        origin = d.pop("origin")

        request_id = d.pop("request_id")

        status = d.pop("status")

        title = d.pop("title")

        full_stats_error = cls(
            detail=detail,
            origin=origin,
            request_id=request_id,
            status=status,
            title=title,
        )

        full_stats_error.additional_properties = d
        return full_stats_error

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
