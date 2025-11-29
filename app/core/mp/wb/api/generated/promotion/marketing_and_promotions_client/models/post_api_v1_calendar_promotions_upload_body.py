from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_api_v1_calendar_promotions_upload_body_data import (
        PostApiV1CalendarPromotionsUploadBodyData,
    )


T = TypeVar("T", bound="PostApiV1CalendarPromotionsUploadBody")


@_attrs_define
class PostApiV1CalendarPromotionsUploadBody:
    """
    Attributes:
        data (PostApiV1CalendarPromotionsUploadBodyData | Unset): Request data
    """

    data: PostApiV1CalendarPromotionsUploadBodyData | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.post_api_v1_calendar_promotions_upload_body_data import (
            PostApiV1CalendarPromotionsUploadBodyData,
        )

        data: dict[str, Any] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_api_v1_calendar_promotions_upload_body_data import (
            PostApiV1CalendarPromotionsUploadBodyData,
        )

        d = dict(src_dict)
        _data = d.pop("data", UNSET)
        data: PostApiV1CalendarPromotionsUploadBodyData | Unset
        if isinstance(_data, Unset):
            data = UNSET
        else:
            data = PostApiV1CalendarPromotionsUploadBodyData.from_dict(_data)

        post_api_v1_calendar_promotions_upload_body = cls(
            data=data,
        )

        post_api_v1_calendar_promotions_upload_body.additional_properties = d
        return post_api_v1_calendar_promotions_upload_body

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
