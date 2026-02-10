from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.post_content_v2_cards_upload_body_item_variants_item import (
        PostContentV2CardsUploadBodyItemVariantsItem,
    )


T = TypeVar("T", bound="PostContentV2CardsUploadBodyItem")


@_attrs_define
class PostContentV2CardsUploadBodyItem:
    """
    Attributes:
        subject_id (int): ID predmeta
        variants (list[PostContentV2CardsUploadBodyItemVariantsItem]):
            [Ob'edinennye](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov) kartochki
            tovarov.<br>Chtoby sozdat' otdel'nuju kartochku, peredajte tol'ko odin ob'ekt
    """

    subject_id: int
    variants: list[PostContentV2CardsUploadBodyItemVariantsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subject_id = self.subject_id

        variants = []
        for variants_item_data in self.variants:
            variants_item = variants_item_data.to_dict()
            variants.append(variants_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subjectID": subject_id,
                "variants": variants,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_cards_upload_body_item_variants_item import (
            PostContentV2CardsUploadBodyItemVariantsItem,
        )

        d = dict(src_dict)
        subject_id = d.pop("subjectID")

        variants = []
        _variants = d.pop("variants")
        for variants_item_data in _variants:
            variants_item = PostContentV2CardsUploadBodyItemVariantsItem.from_dict(
                variants_item_data
            )

            variants.append(variants_item)

        post_content_v2_cards_upload_body_item = cls(
            subject_id=subject_id,
            variants=variants,
        )

        post_content_v2_cards_upload_body_item.additional_properties = d
        return post_content_v2_cards_upload_body_item

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
