from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.put_adv_v0_auction_placements_body_placements_item_placements import (
        PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
    )


T = TypeVar("T", bound="PutAdvV0AuctionPlacementsBodyPlacementsItem")


@_attrs_define
class PutAdvV0AuctionPlacementsBodyPlacementsItem:
    """
    Attributes:
        advert_id (int): Campaign ID
        placements (PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements): Placements
    """

    advert_id: int
    placements: PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.put_adv_v0_auction_placements_body_placements_item_placements import (
            PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
        )

        advert_id = self.advert_id

        placements = self.placements.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "advert_id": advert_id,
            "placements": placements,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.put_adv_v0_auction_placements_body_placements_item_placements import (
            PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
        )

        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        placements = PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements.from_dict(
            d.pop("placements")
        )

        put_adv_v0_auction_placements_body_placements_item = cls(
            advert_id=advert_id,
            placements=placements,
        )

        put_adv_v0_auction_placements_body_placements_item.additional_properties = d
        return put_adv_v0_auction_placements_body_placements_item

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
