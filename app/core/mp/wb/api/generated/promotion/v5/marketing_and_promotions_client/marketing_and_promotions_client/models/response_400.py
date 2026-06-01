from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Response400")


@_attrs_define
class Response400:
    """
    Attributes:
        detail (str): Error details
        origin (str): WB internal service ID Example: camp-api-public-cache.
        request_id (str): Unique request ID Example: 6023d2950af564838f9b44a279d2140c.
        status (int): HTTP status code Example: 400.
        title (str): Error title Example: invalid payload.
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

        response_400 = cls(
            detail=detail,
            origin=origin,
            request_id=request_id,
            status=status,
            title=title,
        )

        response_400.additional_properties = d
        return response_400

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
