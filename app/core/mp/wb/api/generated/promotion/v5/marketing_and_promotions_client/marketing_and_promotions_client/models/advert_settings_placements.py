from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="AdvertSettingsPlacements")


@_attrs_define
class AdvertSettingsPlacements:
    """Placements

    Attributes:
        search (bool): Placement in search:
              - `false` — disabled
              - `true` — enabled
        recommendations (bool): Placement in recommendations:
              - `false` — disabled
              - `true` — enabled
    """

    search: bool
    recommendations: bool
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        search = self.search

        recommendations = self.recommendations

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "search": search,
                "recommendations": recommendations,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        search = d.pop("search")

        recommendations = d.pop("recommendations")

        advert_settings_placements = cls(
            search=search,
            recommendations=recommendations,
        )

        advert_settings_placements.additional_properties = d
        return advert_settings_placements

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
