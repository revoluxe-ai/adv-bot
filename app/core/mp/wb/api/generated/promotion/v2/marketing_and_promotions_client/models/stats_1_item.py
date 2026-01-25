from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Stats1Item")


@_attrs_define
class Stats1Item:
    """
    Attributes:
        views (int | Unset): Kolichestvo prosmotrov
        clicks (int | Unset): Kolichestvo klikov
        atbs (int | Unset): Kolichestvo dobavlenij tovarov v korzinu
        ctr (float | Unset): CTR (click-through rate) — pokazatel' klikabel'nosti, otnoshenie chisla klikov k
            kolichestvu pokazov v ramkah mediakampanii
    """

    views: int | Unset = UNSET
    clicks: int | Unset = UNSET
    atbs: int | Unset = UNSET
    ctr: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        views = self.views

        clicks = self.clicks

        atbs = self.atbs

        ctr = self.ctr

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if views is not UNSET:
            field_dict["views"] = views
        if clicks is not UNSET:
            field_dict["clicks"] = clicks
        if atbs is not UNSET:
            field_dict["atbs"] = atbs
        if ctr is not UNSET:
            field_dict["ctr"] = ctr

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        atbs = d.pop("atbs", UNSET)

        ctr = d.pop("ctr", UNSET)

        stats_1_item = cls(
            views=views,
            clicks=clicks,
            atbs=atbs,
            ctr=ctr,
        )

        stats_1_item.additional_properties = d
        return stats_1_item

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
