from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsListBodySettingsFilter")


@_attrs_define
class PostContentV2GetCardsListBodySettingsFilter:
    """Parametry fil'tratsii

    Attributes:
        with_photo (int | Unset): Fil'tr po foto:
              * `0` — tol'ko kartochki bez foto
              * `1` — tol'ko kartochki s foto
              * `-1` — vse kartochki tovara
             Default: 0.
        text_search (str | Unset): Poisk po artikulu prodavtsa, artikulu WB, barkodu
        tag_i_ds (list[int] | Unset): Poisk po ID jarlykov
        allowed_categories_only (bool | Unset): Fil'tr po kategorii. `true` - tol'ko razreshennye, `false` - vse.
            Ne ispol'zuetsja v pesochnitse
        object_i_ds (list[int] | Unset): Poisk po id predmetov
        brands (list[str] | Unset): Poisk po brendam
        imt_id (int | Unset): Poisk po [ID dlja ob'edinennyh kartochek
            tovarov](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov)
    """

    with_photo: int | Unset = 0
    text_search: str | Unset = UNSET
    tag_i_ds: list[int] | Unset = UNSET
    allowed_categories_only: bool | Unset = UNSET
    object_i_ds: list[int] | Unset = UNSET
    brands: list[str] | Unset = UNSET
    imt_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        with_photo = self.with_photo

        text_search = self.text_search

        tag_i_ds: list[int] | Unset = UNSET
        if not isinstance(self.tag_i_ds, Unset):
            tag_i_ds = self.tag_i_ds

        allowed_categories_only = self.allowed_categories_only

        object_i_ds: list[int] | Unset = UNSET
        if not isinstance(self.object_i_ds, Unset):
            object_i_ds = self.object_i_ds

        brands: list[str] | Unset = UNSET
        if not isinstance(self.brands, Unset):
            brands = self.brands

        imt_id = self.imt_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if with_photo is not UNSET:
            field_dict["withPhoto"] = with_photo
        if text_search is not UNSET:
            field_dict["textSearch"] = text_search
        if tag_i_ds is not UNSET:
            field_dict["tagIDs"] = tag_i_ds
        if allowed_categories_only is not UNSET:
            field_dict["allowedCategoriesOnly"] = allowed_categories_only
        if object_i_ds is not UNSET:
            field_dict["objectIDs"] = object_i_ds
        if brands is not UNSET:
            field_dict["brands"] = brands
        if imt_id is not UNSET:
            field_dict["imtID"] = imt_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        with_photo = d.pop("withPhoto", UNSET)

        text_search = d.pop("textSearch", UNSET)

        tag_i_ds = cast(list[int], d.pop("tagIDs", UNSET))

        allowed_categories_only = d.pop("allowedCategoriesOnly", UNSET)

        object_i_ds = cast(list[int], d.pop("objectIDs", UNSET))

        brands = cast(list[str], d.pop("brands", UNSET))

        imt_id = d.pop("imtID", UNSET)

        post_content_v2_get_cards_list_body_settings_filter = cls(
            with_photo=with_photo,
            text_search=text_search,
            tag_i_ds=tag_i_ds,
            allowed_categories_only=allowed_categories_only,
            object_i_ds=object_i_ds,
            brands=brands,
            imt_id=imt_id,
        )

        post_content_v2_get_cards_list_body_settings_filter.additional_properties = d
        return post_content_v2_get_cards_list_body_settings_filter

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
