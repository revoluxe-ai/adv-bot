from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="V0GetNormQueryStatsItemStat")


@_attrs_define
class V0GetNormQueryStatsItemStat:
    """
    Attributes:
        norm_query (str | Unset): Search cluster
        views (int | Unset): Number of views
        clicks (int | Unset): Number of clicks
        atbs (int | Unset): Number of products added to the basket
        orders (int | Unset): Orders number
        ctr (float | Unset): Slick-through rate — the ratio of clicks to displays, %
        cpc (float | Unset): Cost per click, ₽
        cpm (float | Unset): Average cost per mille, ₽
        avg_pos (float | Unset): Average product position on search results pages
    """

    norm_query: str | Unset = UNSET
    views: int | Unset = UNSET
    clicks: int | Unset = UNSET
    atbs: int | Unset = UNSET
    orders: int | Unset = UNSET
    ctr: float | Unset = UNSET
    cpc: float | Unset = UNSET
    cpm: float | Unset = UNSET
    avg_pos: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        norm_query = self.norm_query

        views = self.views

        clicks = self.clicks

        atbs = self.atbs

        orders = self.orders

        ctr = self.ctr

        cpc = self.cpc

        cpm = self.cpm

        avg_pos = self.avg_pos

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if norm_query is not UNSET:
            field_dict["norm_query"] = norm_query
        if views is not UNSET:
            field_dict["views"] = views
        if clicks is not UNSET:
            field_dict["clicks"] = clicks
        if atbs is not UNSET:
            field_dict["atbs"] = atbs
        if orders is not UNSET:
            field_dict["orders"] = orders
        if ctr is not UNSET:
            field_dict["ctr"] = ctr
        if cpc is not UNSET:
            field_dict["cpc"] = cpc
        if cpm is not UNSET:
            field_dict["cpm"] = cpm
        if avg_pos is not UNSET:
            field_dict["avg_pos"] = avg_pos

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        norm_query = d.pop("norm_query", UNSET)

        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        atbs = d.pop("atbs", UNSET)

        orders = d.pop("orders", UNSET)

        ctr = d.pop("ctr", UNSET)

        cpc = d.pop("cpc", UNSET)

        cpm = d.pop("cpm", UNSET)

        avg_pos = d.pop("avg_pos", UNSET)

        v0_get_norm_query_stats_item_stat = cls(
            norm_query=norm_query,
            views=views,
            clicks=clicks,
            atbs=atbs,
            orders=orders,
            ctr=ctr,
            cpc=cpc,
            cpm=cpm,
            avg_pos=avg_pos,
        )

        v0_get_norm_query_stats_item_stat.additional_properties = d
        return v0_get_norm_query_stats_item_stat

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
