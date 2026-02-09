from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsListResponse200CardsItemDimensions")


@_attrs_define
class PostContentV2GetCardsListResponse200CardsItemDimensions:
    """Gabarity i ves tovara c upakovkoj, sm i kg

    Attributes:
        length (int | Unset): Dlina, sm
        width (int | Unset): Shirina, sm
        height (int | Unset): Vysota, sm
        weight_brutto (float | Unset): Ves, kg<br>Kolichestvo znakov posle zapjatoj <=3
        is_valid (bool | Unset): Potentsial'naja nekorrektnost' gabaritov tovara:

            - `true` — ne vyjavlena. `"isValid":true` ne garantiruet, chto razmery ukazany korrektno. V otdel'nyh sluchajah
            (naprimer, pri sozdanii novoj kategorii tovarov) `"isValid":true` budet vozvraschat'sja pri ljubyh znachenijah,
            krome nulevyh.

            - `false` — ukazannye gabarity znachitel'no otlichajutsja ot srednih po kategorii (predmetu). Rekomenduetsja
            pereproverit', pravil'no li ukazany razmery tovara v upakovke v `santimetrah`. Funktsional'nost' kartochki
            tovara, v tom chisle nachislenie logistiki i hranenija, pri etom ogranichena ne budet. Logistika i hranenie
            prodolzhajut nachisljat'sja — po tekuschim gabaritam. Takzhe `"isValid":false` vozvraschaetsja pri otsutstvii
            znachenij ili nulevom znachenii ljuboj storony.
    """

    length: int | Unset = UNSET
    width: int | Unset = UNSET
    height: int | Unset = UNSET
    weight_brutto: float | Unset = UNSET
    is_valid: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        length = self.length

        width = self.width

        height = self.height

        weight_brutto = self.weight_brutto

        is_valid = self.is_valid

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if length is not UNSET:
            field_dict["length"] = length
        if width is not UNSET:
            field_dict["width"] = width
        if height is not UNSET:
            field_dict["height"] = height
        if weight_brutto is not UNSET:
            field_dict["weightBrutto"] = weight_brutto
        if is_valid is not UNSET:
            field_dict["isValid"] = is_valid

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        length = d.pop("length", UNSET)

        width = d.pop("width", UNSET)

        height = d.pop("height", UNSET)

        weight_brutto = d.pop("weightBrutto", UNSET)

        is_valid = d.pop("isValid", UNSET)

        post_content_v2_get_cards_list_response_200_cards_item_dimensions = cls(
            length=length,
            width=width,
            height=height,
            weight_brutto=weight_brutto,
            is_valid=is_valid,
        )

        post_content_v2_get_cards_list_response_200_cards_item_dimensions.additional_properties = d
        return post_content_v2_get_cards_list_response_200_cards_item_dimensions

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
