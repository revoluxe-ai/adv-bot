from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Field4XxResponse")


@_attrs_define
class Field4XxResponse:
    """
    Attributes:
        detail (Union[Unset, str]): Error details
        origin (Union[Unset, str]): WB internal service ID
        request_id (Union[Unset, str]): Unique request ID
        title (Union[Unset, str]): Error title
    """

    detail: Union[Unset, str] = UNSET
    origin: Union[Unset, str] = UNSET
    request_id: Union[Unset, str] = UNSET
    title: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        detail = self.detail

        origin = self.origin

        request_id = self.request_id

        title = self.title

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if detail is not UNSET:
            field_dict["detail"] = detail
        if origin is not UNSET:
            field_dict["origin"] = origin
        if request_id is not UNSET:
            field_dict["requestId"] = request_id
        if title is not UNSET:
            field_dict["title"] = title

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        detail = d.pop("detail", UNSET)

        origin = d.pop("origin", UNSET)

        request_id = d.pop("requestId", UNSET)

        title = d.pop("title", UNSET)

        field_4_xx_response = cls(
            detail=detail,
            origin=origin,
            request_id=request_id,
            title=title,
        )

        field_4_xx_response.additional_properties = d
        return field_4_xx_response

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
