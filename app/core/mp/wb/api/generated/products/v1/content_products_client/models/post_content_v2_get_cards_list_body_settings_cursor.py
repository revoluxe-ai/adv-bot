from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsListBodySettingsCursor")


@_attrs_define
class PostContentV2GetCardsListBodySettingsCursor:
    """Kursor

    Attributes:
        limit (int | Unset): Skol'ko kartochek tovarov vydat' v otvete Default: 10.
        updated_at (str | Unset): Data i vremja izmenenija
        nm_id (int | Unset): Artikul WB, s kotorogo nado zaprashivat' sledujuschij spisok kartochek tovarov
    """

    limit: int | Unset = 10
    updated_at: str | Unset = UNSET
    nm_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        limit = self.limit

        updated_at = self.updated_at

        nm_id = self.nm_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if limit is not UNSET:
            field_dict["limit"] = limit
        if updated_at is not UNSET:
            field_dict["updatedAt"] = updated_at
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        limit = d.pop("limit", UNSET)

        updated_at = d.pop("updatedAt", UNSET)

        nm_id = d.pop("nmID", UNSET)

        post_content_v2_get_cards_list_body_settings_cursor = cls(
            limit=limit,
            updated_at=updated_at,
            nm_id=nm_id,
        )

        post_content_v2_get_cards_list_body_settings_cursor.additional_properties = d
        return post_content_v2_get_cards_list_body_settings_cursor

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
