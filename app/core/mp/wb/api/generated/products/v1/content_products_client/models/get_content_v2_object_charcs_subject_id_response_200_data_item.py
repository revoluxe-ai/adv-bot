from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetContentV2ObjectCharcsSubjectIdResponse200DataItem")


@_attrs_define
class GetContentV2ObjectCharcsSubjectIdResponse200DataItem:
    """
    Attributes:
        charc_id (int | Unset): ID harakteristiki
        subject_name (str | Unset): Nazvanie predmeta
        subject_id (int | Unset): ID predmeta
        name (str | Unset): Nazvanie harakteristiki
        required (bool | Unset): - `true` - harakteristiku neobhodimo objazatel'no ukazat' v kartochke tovara
            - `false` - harakteristiku neobjazatel'no ukazyvat'
        unit_name (str | Unset): Edinitsa izmerenija
        max_count (int | Unset): Maksimal'noe kolichestvo znachenij, kotoroe mozhno prisvoit' harakteristike pri
            [sozdanii](./work-with-products#tag/Sozdanie-kartochek-tovarov) ili [redaktirovanii](./work-with-
            products#tag/Kartochki-tovarov/paths/~1content~1v2~1cards~1update/post) kartochek tovarov.
            <br>
            Ispol'zuetsja tol'ko dlja harakteristik s `"charcType":1` — massiv strok.
            <br>
            Harakteristikam s `"charcType":4` — chislo, mozhno prisvoit' tol'ko odno znachenie.
            <br><br>
            Esli `"maxCount":0`, kolichestvo znachenij ne ogranicheno
        popular (bool | Unset): Harakteristika populjarna u pol'zovatelej (true - da, false - net)
        charc_type (int | Unset): Tip dannyh harakteristiki, kotoryj neobhodimo ispol'zovat' pri [sozdanii](./work-with-
            products#tag/Sozdanie-kartochek-tovarov) ili [redaktirovanii](./work-with-products#tag/Kartochki-
            tovarov/paths/~1content~1v2~1cards~1update/post) kartochek tovarov:
              -  `1` — massiv strok
              -  `4` — chislo (tseloe libo s desjatichnoj drob'ju)
              -  `0` — harakteristika ne ispol'zuetsja
    """

    charc_id: int | Unset = UNSET
    subject_name: str | Unset = UNSET
    subject_id: int | Unset = UNSET
    name: str | Unset = UNSET
    required: bool | Unset = UNSET
    unit_name: str | Unset = UNSET
    max_count: int | Unset = UNSET
    popular: bool | Unset = UNSET
    charc_type: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        charc_id = self.charc_id

        subject_name = self.subject_name

        subject_id = self.subject_id

        name = self.name

        required = self.required

        unit_name = self.unit_name

        max_count = self.max_count

        popular = self.popular

        charc_type = self.charc_type

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if charc_id is not UNSET:
            field_dict["charcID"] = charc_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if subject_id is not UNSET:
            field_dict["subjectID"] = subject_id
        if name is not UNSET:
            field_dict["name"] = name
        if required is not UNSET:
            field_dict["required"] = required
        if unit_name is not UNSET:
            field_dict["unitName"] = unit_name
        if max_count is not UNSET:
            field_dict["maxCount"] = max_count
        if popular is not UNSET:
            field_dict["popular"] = popular
        if charc_type is not UNSET:
            field_dict["charcType"] = charc_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        charc_id = d.pop("charcID", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        subject_id = d.pop("subjectID", UNSET)

        name = d.pop("name", UNSET)

        required = d.pop("required", UNSET)

        unit_name = d.pop("unitName", UNSET)

        max_count = d.pop("maxCount", UNSET)

        popular = d.pop("popular", UNSET)

        charc_type = d.pop("charcType", UNSET)

        get_content_v2_object_charcs_subject_id_response_200_data_item = cls(
            charc_id=charc_id,
            subject_name=subject_name,
            subject_id=subject_id,
            name=name,
            required=required,
            unit_name=unit_name,
            max_count=max_count,
            popular=popular,
            charc_type=charc_type,
        )

        get_content_v2_object_charcs_subject_id_response_200_data_item.additional_properties = d
        return get_content_v2_object_charcs_subject_id_response_200_data_item

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
