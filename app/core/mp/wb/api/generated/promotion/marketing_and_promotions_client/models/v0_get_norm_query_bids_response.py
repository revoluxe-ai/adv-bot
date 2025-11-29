from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_bids_item import V0GetNormQueryBidsItem


T = TypeVar("T", bound="V0GetNormQueryBidsResponse")


@_attrs_define
class V0GetNormQueryBidsResponse:
    """
    Attributes:
        bids (list[V0GetNormQueryBidsItem]):
    """

    bids: list[V0GetNormQueryBidsItem]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.v0_get_norm_query_bids_item import V0GetNormQueryBidsItem

        bids = []
        for bids_item_data in self.bids:
            bids_item = bids_item_data.to_dict()
            bids.append(bids_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "bids": bids,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.v0_get_norm_query_bids_item import V0GetNormQueryBidsItem

        d = dict(src_dict)
        bids = []
        _bids = d.pop("bids")
        for bids_item_data in _bids:
            bids_item = V0GetNormQueryBidsItem.from_dict(bids_item_data)

            bids.append(bids_item)

        v0_get_norm_query_bids_response = cls(
            bids=bids,
        )

        v0_get_norm_query_bids_response.additional_properties = d
        return v0_get_norm_query_bids_response

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
