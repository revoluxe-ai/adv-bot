from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0GetNormQueryMinusResponseItem")


@_attrs_define
class V0GetNormQueryMinusResponseItem:
    """
    Attributes:
        advert_id (int): Campaign ID
        nm_id (int): WB article
        norm_queries (list[str] | Unset): List of minus-phrases
    """

    advert_id: int
    nm_id: int
    norm_queries: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        nm_id = self.nm_id

        norm_queries: list[str] | Unset = UNSET
        if not isinstance(self.norm_queries, Unset):
            norm_queries = self.norm_queries

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "advert_id": advert_id,
            "nm_id": nm_id,
        })
        if norm_queries is not UNSET:
            field_dict["norm_queries"] = norm_queries

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        advert_id = d.pop("advert_id")

        nm_id = d.pop("nm_id")

        norm_queries = cast(list[str], d.pop("norm_queries", UNSET))

        v0_get_norm_query_minus_response_item = cls(
            advert_id=advert_id,
            nm_id=nm_id,
            norm_queries=norm_queries,
        )

        v0_get_norm_query_minus_response_item.additional_properties = d
        return v0_get_norm_query_minus_response_item

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
