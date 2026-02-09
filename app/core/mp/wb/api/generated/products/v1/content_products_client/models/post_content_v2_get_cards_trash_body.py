from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_get_cards_trash_body_settings import (
        PostContentV2GetCardsTrashBodySettings,
    )


T = TypeVar("T", bound="PostContentV2GetCardsTrashBody")


@_attrs_define
class PostContentV2GetCardsTrashBody:
    """
    Attributes:
        settings (PostContentV2GetCardsTrashBodySettings | Unset): Nastrojki
    """

    settings: PostContentV2GetCardsTrashBodySettings | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        settings: dict[str, Any] | Unset = UNSET
        if not isinstance(self.settings, Unset):
            settings = self.settings.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if settings is not UNSET:
            field_dict["settings"] = settings

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_get_cards_trash_body_settings import (
            PostContentV2GetCardsTrashBodySettings,
        )

        d = dict(src_dict)
        _settings = d.pop("settings", UNSET)
        settings: PostContentV2GetCardsTrashBodySettings | Unset
        if isinstance(_settings, Unset):
            settings = UNSET
        else:
            settings = PostContentV2GetCardsTrashBodySettings.from_dict(_settings)

        post_content_v2_get_cards_trash_body = cls(
            settings=settings,
        )

        post_content_v2_get_cards_trash_body.additional_properties = d
        return post_content_v2_get_cards_trash_body

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
