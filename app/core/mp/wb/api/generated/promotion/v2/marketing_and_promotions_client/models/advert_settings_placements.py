from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="AdvertSettingsPlacements")


@_attrs_define
class AdvertSettingsPlacements:
    """Mesta razmeschenija

    Attributes:
        search (bool): Razmeschenie v poiske:
              - `false` — otkljucheno
              - `true` — vkljucheno
        recommendations (bool): Razmeschenie v rekomendatsijah:
              - `false` — otkljucheno
              - `true` — vkljucheno
    """

    search: bool
    recommendations: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        search = self.search

        recommendations = self.recommendations

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "search": search,
                "recommendations": recommendations,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any] | None) -> T:
        d = dict(src_dict or {})
        search = d.pop("search", False)
        if search is None:
            search = False

        recommendations = d.pop("recommendations", False)
        if recommendations is None:
            recommendations = False

        advert_settings_placements = cls(
            search=search,
            recommendations=recommendations,
        )

        advert_settings_placements.additional_properties = d
        return advert_settings_placements

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
