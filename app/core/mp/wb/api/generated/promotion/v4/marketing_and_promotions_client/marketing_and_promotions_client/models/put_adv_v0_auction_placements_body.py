from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.put_adv_v0_auction_placements_body_placements_item import (
        PutAdvV0AuctionPlacementsBodyPlacementsItem,
    )


T = TypeVar("T", bound="PutAdvV0AuctionPlacementsBody")


@_attrs_define
class PutAdvV0AuctionPlacementsBody:
    """
    Attributes:
        placements (List['PutAdvV0AuctionPlacementsBodyPlacementsItem']): Placements in campaigns
    """

    placements: List["PutAdvV0AuctionPlacementsBodyPlacementsItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        placements = []
        for placements_item_data in self.placements:
            placements_item = placements_item_data.to_dict()
            placements.append(placements_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "placements": placements,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.put_adv_v0_auction_placements_body_placements_item import (
            PutAdvV0AuctionPlacementsBodyPlacementsItem,
        )

        d = src_dict.copy()
        placements = []
        _placements = d.pop("placements")
        for placements_item_data in _placements:
            placements_item = PutAdvV0AuctionPlacementsBodyPlacementsItem.from_dict(
                placements_item_data
            )

            placements.append(placements_item)

        put_adv_v0_auction_placements_body = cls(
            placements=placements,
        )

        put_adv_v0_auction_placements_body.additional_properties = d
        return put_adv_v0_auction_placements_body

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
