from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostApiV1CalendarPromotionsUploadResponse200Data")


@_attrs_define
class PostApiV1CalendarPromotionsUploadResponse200Data:
    """Response data

    Attributes:
        already_exists (bool | Unset): Upload with this data already exists
        upload_id (int | Unset): Upload ID Example: 11.
    """

    already_exists: bool | Unset = UNSET
    upload_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        already_exists = self.already_exists

        upload_id = self.upload_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if already_exists is not UNSET:
            field_dict["alreadyExists"] = already_exists
        if upload_id is not UNSET:
            field_dict["uploadID"] = upload_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        already_exists = d.pop("alreadyExists", UNSET)

        upload_id = d.pop("uploadID", UNSET)

        post_api_v1_calendar_promotions_upload_response_200_data = cls(
            already_exists=already_exists,
            upload_id=upload_id,
        )

        post_api_v1_calendar_promotions_upload_response_200_data.additional_properties = d
        return post_api_v1_calendar_promotions_upload_response_200_data

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
