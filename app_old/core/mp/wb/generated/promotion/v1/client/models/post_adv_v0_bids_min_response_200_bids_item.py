from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.post_adv_v0_bids_min_response_200_bids_item_bids_item import (
        PostAdvV0BidsMinResponse200BidsItemBidsItem,
    )


T = TypeVar("T", bound="PostAdvV0BidsMinResponse200BidsItem")


@_attrs_define
class PostAdvV0BidsMinResponse200BidsItem:
    """
    Attributes:
        bids (list['PostAdvV0BidsMinResponse200BidsItemBidsItem']): Spisok stavok po zonam pokazov
        nm_id (int): Artikul WB
    """

    bids: list["PostAdvV0BidsMinResponse200BidsItemBidsItem"]
    nm_id: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bids = []
        for bids_item_data in self.bids:
            bids_item = bids_item_data.to_dict()
            bids.append(bids_item)

        nm_id = self.nm_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bids": bids,
                "nm_id": nm_id,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_adv_v0_bids_min_response_200_bids_item_bids_item import (
            PostAdvV0BidsMinResponse200BidsItemBidsItem,
        )

        d = dict(src_dict)
        bids = []
        _bids = d.pop("bids")
        for bids_item_data in _bids:
            bids_item = PostAdvV0BidsMinResponse200BidsItemBidsItem.from_dict(
                bids_item_data
            )

            bids.append(bids_item)

        nm_id = d.pop("nm_id")

        post_adv_v0_bids_min_response_200_bids_item = cls(
            bids=bids,
            nm_id=nm_id,
        )

        post_adv_v0_bids_min_response_200_bids_item.additional_properties = d
        return post_adv_v0_bids_min_response_200_bids_item

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
