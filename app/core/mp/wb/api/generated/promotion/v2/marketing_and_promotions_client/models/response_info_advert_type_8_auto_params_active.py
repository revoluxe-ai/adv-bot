from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseInfoAdvertType8AutoParamsActive")


@_attrs_define
class ResponseInfoAdvertType8AutoParamsActive:
    """Mesta razmeschenija

    Attributes:
        carousel (bool | Unset): Kartochka tovara
              - `false` — otkljucheno
              - `true` — vkljucheno
        recom (bool | Unset): Rekomendatsii na glavnoj
              - `false` — otkljucheno
              - `true` — vkljucheno
        booster (bool | Unset): Ruchnaja stavka
              - `false` — otkljucheno
              - `true` — vkljucheno
    """

    carousel: bool | Unset = UNSET
    recom: bool | Unset = UNSET
    booster: bool | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        carousel = self.carousel

        recom = self.recom

        booster = self.booster

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if carousel is not UNSET:
            field_dict["carousel"] = carousel
        if recom is not UNSET:
            field_dict["recom"] = recom
        if booster is not UNSET:
            field_dict["booster"] = booster

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        carousel = d.pop("carousel", UNSET)

        recom = d.pop("recom", UNSET)

        booster = d.pop("booster", UNSET)

        response_info_advert_type_8_auto_params_active = cls(
            carousel=carousel,
            recom=recom,
            booster=booster,
        )

        response_info_advert_type_8_auto_params_active.additional_properties = d
        return response_info_advert_type_8_auto_params_active

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
