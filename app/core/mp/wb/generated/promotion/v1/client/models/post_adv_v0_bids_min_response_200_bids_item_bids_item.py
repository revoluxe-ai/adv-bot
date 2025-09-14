from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.placement_type import PlacementType

T = TypeVar("T", bound="PostAdvV0BidsMinResponse200BidsItemBidsItem")


@_attrs_define
class PostAdvV0BidsMinResponse200BidsItemBidsItem:
    """
    Attributes:
        type_ (PlacementType): Zony pokazov:
              - `search` — poisk
              - `recommendation` — rekomendatsii
              - `combined` — poisk i rekomendatsii
        value (int): Minimal'naja stavka
    """

    type_: PlacementType
    value: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_.value

        value = self.value

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "type": type_,
                "value": value,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = PlacementType(d.pop("type"))

        value = d.pop("value")

        post_adv_v0_bids_min_response_200_bids_item_bids_item = cls(
            type_=type_,
            value=value,
        )

        post_adv_v0_bids_min_response_200_bids_item_bids_item.additional_properties = d
        return post_adv_v0_bids_min_response_200_bids_item_bids_item

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
