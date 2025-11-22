from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Response429Download")


@_attrs_define
class Response429Download:
    """Slishkom mnogo zaprosov

    Example:
        {'title': 'too many requests', 'detail': 'limited by c122a060-a7fb-4bb4-abb0-32fd4e18d489', 'code':
            '07e4668e-ac2242c5c8c5-[UK-4dx7JUdskGZ]', 'requestId': '9d3c02cc698f8b041c661a7c28bed293', 'origin': 's2s-api-
            auth-stat', 'status': 429, 'statusText': 'Too Many Requests', 'timestamp': '2024-09-30T06:52:38Z'}

    Attributes:
        title (Union[Unset, str]): Zagolovok oshibki
        detail (Union[Unset, str]): Detali oshibki
        code (Union[Unset, str]): Vnutrennij kod oshibki
        request_id (Union[Unset, str]): Unikal'nyj ID zaprosa
        origin (Union[Unset, str]): ID vnutrennego servisa WB
        status (Union[Unset, float]): HTTP status-kod
        status_text (Union[Unset, str]): Rasshifrovka HTTP status-koda
        timestamp (Union[Unset, str]): Data i vremja zaprosa
    """

    title: Union[Unset, str] = UNSET
    detail: Union[Unset, str] = UNSET
    code: Union[Unset, str] = UNSET
    request_id: Union[Unset, str] = UNSET
    origin: Union[Unset, str] = UNSET
    status: Union[Unset, float] = UNSET
    status_text: Union[Unset, str] = UNSET
    timestamp: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        title = self.title

        detail = self.detail

        code = self.code

        request_id = self.request_id

        origin = self.origin

        status = self.status

        status_text = self.status_text

        timestamp = self.timestamp

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
        if detail is not UNSET:
            field_dict["detail"] = detail
        if code is not UNSET:
            field_dict["code"] = code
        if request_id is not UNSET:
            field_dict["requestId"] = request_id
        if origin is not UNSET:
            field_dict["origin"] = origin
        if status is not UNSET:
            field_dict["status"] = status
        if status_text is not UNSET:
            field_dict["statusText"] = status_text
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        title = d.pop("title", UNSET)

        detail = d.pop("detail", UNSET)

        code = d.pop("code", UNSET)

        request_id = d.pop("requestId", UNSET)

        origin = d.pop("origin", UNSET)

        status = d.pop("status", UNSET)

        status_text = d.pop("statusText", UNSET)

        timestamp = d.pop("timestamp", UNSET)

        response_429_download = cls(
            title=title,
            detail=detail,
            code=code,
            request_id=request_id,
            origin=origin,
            status=status,
            status_text=status_text,
            timestamp=timestamp,
        )

        response_429_download.additional_properties = d
        return response_429_download

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
