from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.post_api_advert_v1_bids_min_response_200_bids_item import (
        PostApiAdvertV1BidsMinResponse200BidsItem,
    )


T = TypeVar("T", bound="PostApiAdvertV1BidsMinResponse200")


@_attrs_define
class PostApiAdvertV1BidsMinResponse200:
    """
    Attributes:
        bids (list[PostApiAdvertV1BidsMinResponse200BidsItem]): Spisok kartochek tovarov so stavkami
    """

    bids: list[PostApiAdvertV1BidsMinResponse200BidsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        bids = []
        for bids_item_data in self.bids:
            bids_item = bids_item_data.to_dict()
            bids.append(bids_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "bids": bids,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_api_advert_v1_bids_min_response_200_bids_item import (
            PostApiAdvertV1BidsMinResponse200BidsItem,
        )

        d = dict(src_dict)
        bids = []
        _bids = d.pop("bids")
        for bids_item_data in _bids:
            bids_item = PostApiAdvertV1BidsMinResponse200BidsItem.from_dict(
                bids_item_data
            )

            bids.append(bids_item)

        post_api_advert_v1_bids_min_response_200 = cls(
            bids=bids,
        )

        post_api_advert_v1_bids_min_response_200.additional_properties = d
        return post_api_advert_v1_bids_min_response_200

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
