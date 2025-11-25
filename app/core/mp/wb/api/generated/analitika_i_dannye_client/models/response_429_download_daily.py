from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Response429DownloadDaily")


@_attrs_define
class Response429DownloadDaily:
    """
    Example:
        {'title': 'Too many requests', 'detail': 'The daily response limit has been exceeded. The maximum number is
            20.', 'requestId': '51b7828b-e298-4dfa-b7cd-45ab179921d393', 'origin': 'analytics-open-api'}

    Attributes:
        title (str): Zagolovok oshibki
        detail (str): Detali oshibki
        request_id (str): Unikal'nyj ID zaprosa
        origin (str): ID vnutrennego servisa WB
    """

    title: str
    detail: str
    request_id: str
    origin: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        title = self.title

        detail = self.detail

        request_id = self.request_id

        origin = self.origin

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "title": title,
                "detail": detail,
                "requestId": request_id,
                "origin": origin,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        title = d.pop("title")

        detail = d.pop("detail")

        request_id = d.pop("requestId")

        origin = d.pop("origin")

        response_429_download_daily = cls(
            title=title,
            detail=detail,
            request_id=request_id,
            origin=origin,
        )

        response_429_download_daily.additional_properties = d
        return response_429_download_daily

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
