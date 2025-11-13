from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements")


@_attrs_define
class PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements:
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

        put_adv_v0_auction_placements_body_placements_item_placements = cls(
            search=search,
            recommendations=recommendations,
        )

        put_adv_v0_auction_placements_body_placements_item_placements.additional_properties = d
        return put_adv_v0_auction_placements_body_placements_item_placements

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
