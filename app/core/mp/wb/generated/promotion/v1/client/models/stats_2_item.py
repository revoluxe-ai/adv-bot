from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Stats2Item")


@_attrs_define
class Stats2Item:
    """
    Attributes:
        views (Union[Unset, int]): Kolichestvo prosmotrov
        clicks (Union[Unset, int]): Kolichestvo klikov
        atbs (Union[Unset, int]): Kolichestvo dobavlenij tovarov v korzinu
        orders (Union[Unset, int]): Kolichestvo zakazov
        cr (Union[Unset, float]): CR(conversion rate) — otnoshenie kolichestva zakazov k obschemu kolichestvu
            poseschenij mediakampanii
        ctr (Union[Unset, float]): CTR (click-through rate) — pokazatel' klikabel'nosti, otnoshenie chisla klikov k
            kolichestvu pokazov v ramkah mediakampanii
    """

    views: Union[Unset, int] = UNSET
    clicks: Union[Unset, int] = UNSET
    atbs: Union[Unset, int] = UNSET
    orders: Union[Unset, int] = UNSET
    cr: Union[Unset, float] = UNSET
    ctr: Union[Unset, float] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        views = self.views

        clicks = self.clicks

        atbs = self.atbs

        orders = self.orders

        cr = self.cr

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
        if orders is not UNSET:
            field_dict["orders"] = orders
        if cr is not UNSET:
            field_dict["cr"] = cr
        if ctr is not UNSET:
            field_dict["ctr"] = ctr

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        atbs = d.pop("atbs", UNSET)

        orders = d.pop("orders", UNSET)

        cr = d.pop("cr", UNSET)

        ctr = d.pop("ctr", UNSET)

        stats_2_item = cls(
            views=views,
            clicks=clicks,
            atbs=atbs,
            orders=orders,
            cr=cr,
            ctr=ctr,
        )

        stats_2_item.additional_properties = d
        return stats_2_item

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
