from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Response403Retentions")


@_attrs_define
class Response403Retentions:
    """
    Attributes:
        title (Union[Unset, str]): Error title Example: access denied.
        status (Union[Unset, int]): HTTP status code Example: 403.
        detail (Union[Unset, str]): Error details Example: abac: access denied.
        request_id (Union[Unset, str]): Unique request ID Example: 31db50b5-14c0-4f4e-965e-6e1f9607ee78.
        origin (Union[Unset, str]): WB internal service ID Example: dimension-penalty.
    """

    title: Union[Unset, str] = UNSET
    status: Union[Unset, int] = UNSET
    detail: Union[Unset, str] = UNSET
    request_id: Union[Unset, str] = UNSET
    origin: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        title = self.title

        status = self.status

        detail = self.detail

        request_id = self.request_id

        origin = self.origin

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if title is not UNSET:
            field_dict["title"] = title
        if status is not UNSET:
            field_dict["status"] = status
        if detail is not UNSET:
            field_dict["detail"] = detail
        if request_id is not UNSET:
            field_dict["requestId"] = request_id
        if origin is not UNSET:
            field_dict["origin"] = origin

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        title = d.pop("title", UNSET)

        status = d.pop("status", UNSET)

        detail = d.pop("detail", UNSET)

        request_id = d.pop("requestId", UNSET)

        origin = d.pop("origin", UNSET)

        response_403_retentions = cls(
            title=title,
            status=status,
            detail=detail,
            request_id=request_id,
            origin=origin,
        )

        response_403_retentions.additional_properties = d
        return response_403_retentions

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
