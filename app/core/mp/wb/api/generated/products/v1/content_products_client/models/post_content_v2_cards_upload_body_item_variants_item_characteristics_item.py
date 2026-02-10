from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar(
    "T", bound="PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem"
)


@_attrs_define
class PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem:
    """
    Attributes:
        id (int): ID harakteristiki
        value (Any): Znachenija harakteristiki.
            <br>
            Tip dannyh — massiv strok ili chislo — zavisit ot tipa harakteristiki, sm. opisanie polja `charcType` v metode
            [Harakteristiki predmeta](./work-with-products#tag/Kategorii-predmety-i-
            harakteristiki/paths/~1content~1v2~1object~1charcs~1%7BsubjectId%7D/get).
            <br>
            Dopustimoe kolichestvo znachenij otobrazheno v pole `maxCount` togo zhe metoda
    """

    id: int
    value: Any
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        value = d.pop("value")

        post_content_v2_cards_upload_body_item_variants_item_characteristics_item = cls(
            id=id,
            value=value,
        )

        post_content_v2_cards_upload_body_item_variants_item_characteristics_item.additional_properties = d
        return post_content_v2_cards_upload_body_item_variants_item_characteristics_item

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
