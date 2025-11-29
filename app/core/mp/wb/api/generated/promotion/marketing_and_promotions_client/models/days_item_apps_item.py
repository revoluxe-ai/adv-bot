from __future__ import annotations

from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.days_item_apps_item_nm_item import DaysItemAppsItemNmItem


T = TypeVar("T", bound="DaysItemAppsItem")


@_attrs_define
class DaysItemAppsItem:
    """
    Attributes:
        views (int | Unset): Number of views
        clicks (int | Unset): Number of clicks
        ctr (float | Unset): Click-Through Rate, ratio of clicks to displays, %
        cpc (float | Unset): Average cost per click, ₽
        sum_ (float | Unset): Expenses, ₽
        atbs (int | Unset): Number of products added to the basket
        orders (int | Unset): Orders number
        cr (float | Unset): CR(conversion rate) is the ratio of the number of orders to the total number of visits to
            the campaign
        shks (int | Unset): Number of ordered products, pcs
        sum_price (float | Unset): Orders amount, ₽
        nm (list[DaysItemAppsItemNmItem] | Unset): Statistics block for WB articles
        app_type (int | Unset): Platform type (`1` — website, `32` — Android, `64` — IOS)
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
    nm: list[DaysItemAppsItemNmItem] | Unset = UNSET
    app_type: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.days_item_apps_item_nm_item import DaysItemAppsItemNmItem

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

        nm: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.nm, Unset):
            nm = []
            for nm_item_data in self.nm:
                nm_item = nm_item_data.to_dict()
                nm.append(nm_item)

        app_type = self.app_type

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
        if nm is not UNSET:
            field_dict["nm"] = nm
        if app_type is not UNSET:
            field_dict["appType"] = app_type

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.days_item_apps_item_nm_item import DaysItemAppsItemNmItem

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

        _nm = d.pop("nm", UNSET)
        nm: list[DaysItemAppsItemNmItem] | Unset = UNSET
        if _nm is not UNSET:
            nm = []
            for nm_item_data in _nm:
                nm_item = DaysItemAppsItemNmItem.from_dict(nm_item_data)

                nm.append(nm_item)

        app_type = d.pop("appType", UNSET)

        days_item_apps_item = cls(
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
            nm=nm,
            app_type=app_type,
        )

        days_item_apps_item.additional_properties = d
        return days_item_apps_item

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
