from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_get_cards_list_body_settings_cursor import (
        PostContentV2GetCardsListBodySettingsCursor,
    )
    from ..models.post_content_v2_get_cards_list_body_settings_filter import (
        PostContentV2GetCardsListBodySettingsFilter,
    )
    from ..models.post_content_v2_get_cards_list_body_settings_sort import (
        PostContentV2GetCardsListBodySettingsSort,
    )


T = TypeVar("T", bound="PostContentV2GetCardsListBodySettings")


@_attrs_define
class PostContentV2GetCardsListBodySettings:
    """Nastrojki

    Attributes:
        sort (PostContentV2GetCardsListBodySettingsSort | Unset): Parametr sortirovki
        filter_ (PostContentV2GetCardsListBodySettingsFilter | Unset): Parametry fil'tratsii
        cursor (PostContentV2GetCardsListBodySettingsCursor | Unset): Kursor
    """

    sort: PostContentV2GetCardsListBodySettingsSort | Unset = UNSET
    filter_: PostContentV2GetCardsListBodySettingsFilter | Unset = UNSET
    cursor: PostContentV2GetCardsListBodySettingsCursor | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        sort: dict[str, Any] | Unset = UNSET
        if not isinstance(self.sort, Unset):
            sort = self.sort.to_dict()

        filter_: dict[str, Any] | Unset = UNSET
        if not isinstance(self.filter_, Unset):
            filter_ = self.filter_.to_dict()

        cursor: dict[str, Any] | Unset = UNSET
        if not isinstance(self.cursor, Unset):
            cursor = self.cursor.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if sort is not UNSET:
            field_dict["sort"] = sort
        if filter_ is not UNSET:
            field_dict["filter"] = filter_
        if cursor is not UNSET:
            field_dict["cursor"] = cursor

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_get_cards_list_body_settings_cursor import (
            PostContentV2GetCardsListBodySettingsCursor,
        )
        from ..models.post_content_v2_get_cards_list_body_settings_filter import (
            PostContentV2GetCardsListBodySettingsFilter,
        )
        from ..models.post_content_v2_get_cards_list_body_settings_sort import (
            PostContentV2GetCardsListBodySettingsSort,
        )

        d = dict(src_dict)
        _sort = d.pop("sort", UNSET)
        sort: PostContentV2GetCardsListBodySettingsSort | Unset
        if isinstance(_sort, Unset):
            sort = UNSET
        else:
            sort = PostContentV2GetCardsListBodySettingsSort.from_dict(_sort)

        _filter_ = d.pop("filter", UNSET)
        filter_: PostContentV2GetCardsListBodySettingsFilter | Unset
        if isinstance(_filter_, Unset):
            filter_ = UNSET
        else:
            filter_ = PostContentV2GetCardsListBodySettingsFilter.from_dict(_filter_)

        _cursor = d.pop("cursor", UNSET)
        cursor: PostContentV2GetCardsListBodySettingsCursor | Unset
        if isinstance(_cursor, Unset):
            cursor = UNSET
        else:
            cursor = PostContentV2GetCardsListBodySettingsCursor.from_dict(_cursor)

        post_content_v2_get_cards_list_body_settings = cls(
            sort=sort,
            filter_=filter_,
            cursor=cursor,
        )

        post_content_v2_get_cards_list_body_settings.additional_properties = d
        return post_content_v2_get_cards_list_body_settings

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
