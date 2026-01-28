from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DaysItemAppsItemNmItem")


@_attrs_define
class DaysItemAppsItemNmItem:
    """
    Attributes:
        views (int | Unset): Kolichestvo prosmotrov
        clicks (int | Unset): Kolichestvo klikov
        ctr (float | Unset): Pokazatel' klikabel'nosti, otnoshenie chisla klikov k kolichestvu pokazov, %
        cpc (float | Unset): Srednjaja stoimost' klika, ₽
        sum_ (float | Unset): Zatraty, ₽
        atbs (int | Unset): Kolichestvo dobavlenij tovarov v korzinu
        orders (int | Unset): Kolichestvo zakazov
        cr (float | Unset): CR(conversion rate) — otnoshenie kolichestva zakazov k obschemu kolichestvu poseschenij
            kampanii
        shks (int | Unset): Kolichestvo zakazannyh tovarov, sht.
        sum_price (float | Unset): Zakazov na summu, ₽
        name (str | Unset): Nazvanie tovara
        nm_id (int | Unset): ID artikula WB
    """

    views: int | Unset = UNSET
    clicks: int | Unset = UNSET
    ctr: float | Unset = UNSET
    cpc: float | Unset = UNSET
    sum_: float | Unset = UNSET
    atbs: int | Unset = UNSET
    orders: int | Unset = UNSET
    cr: float | Unset = UNSET
    shks: int | Unset = UNSET
    sum_price: float | Unset = UNSET
    name: str | Unset = UNSET
    nm_id: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        views = self.views

        clicks = self.clicks

        ctr = self.ctr

        cpc = self.cpc

        sum_ = self.sum_

        atbs = self.atbs

        orders = self.orders

        cr = self.cr

        shks = self.shks

        sum_price = self.sum_price

        name = self.name

        nm_id = self.nm_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if views is not UNSET:
            field_dict["views"] = views
        if clicks is not UNSET:
            field_dict["clicks"] = clicks
        if ctr is not UNSET:
            field_dict["ctr"] = ctr
        if cpc is not UNSET:
            field_dict["cpc"] = cpc
        if sum_ is not UNSET:
            field_dict["sum"] = sum_
        if atbs is not UNSET:
            field_dict["atbs"] = atbs
        if orders is not UNSET:
            field_dict["orders"] = orders
        if cr is not UNSET:
            field_dict["cr"] = cr
        if shks is not UNSET:
            field_dict["shks"] = shks
        if sum_price is not UNSET:
            field_dict["sum_price"] = sum_price
        if name is not UNSET:
            field_dict["name"] = name
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        ctr = d.pop("ctr", UNSET)

        cpc = d.pop("cpc", UNSET)

        sum_ = d.pop("sum", UNSET)

        atbs = d.pop("atbs", UNSET)

        orders = d.pop("orders", UNSET)

        cr = d.pop("cr", UNSET)

        shks = d.pop("shks", UNSET)

        sum_price = d.pop("sum_price", UNSET)

        name = d.pop("name", UNSET)

        nm_id = d.pop("nmId", UNSET)

        days_item_apps_item_nm_item = cls(
            views=views,
            clicks=clicks,
            ctr=ctr,
            cpc=cpc,
            sum_=sum_,
            atbs=atbs,
            orders=orders,
            cr=cr,
            shks=shks,
            sum_price=sum_price,
            name=name,
            nm_id=nm_id,
        )

        days_item_apps_item_nm_item.additional_properties = d
        return days_item_apps_item_nm_item

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
