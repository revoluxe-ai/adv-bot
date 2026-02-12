from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsTrashResponse200Cursor")


@_attrs_define
class PostContentV2GetCardsTrashResponse200Cursor:
    """Paginator

    Attributes:
        trashed_at (str | Unset): Data i vremja, s kotoryh nado zaprashivat' sledujuschij spisok kartochek tovarov
        nm_id (int | Unset): Artikul WB, s kotorogo nado zaprashivat' sledujuschij spisok kartochek tovarov
        total (int | Unset): Kolichestvo vozvraschennyh kartochek tovarov
    """

    trashed_at: str | Unset = UNSET
    nm_id: int | Unset = UNSET
    total: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        trashed_at = self.trashed_at

        nm_id = self.nm_id

        total = self.total

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if trashed_at is not UNSET:
            field_dict["trashedAt"] = trashed_at
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if total is not UNSET:
            field_dict["total"] = total

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        trashed_at = d.pop("trashedAt", UNSET)

        nm_id = d.pop("nmID", UNSET)

        total = d.pop("total", UNSET)

        post_content_v2_get_cards_trash_response_200_cursor = cls(
            trashed_at=trashed_at,
            nm_id=nm_id,
            total=total,
        )

        post_content_v2_get_cards_trash_response_200_cursor.additional_properties = d
        return post_content_v2_get_cards_trash_response_200_cursor

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
