from __future__ import annotations

import datetime
from collections.abc import Generator, Mapping
from typing import TYPE_CHECKING, Any, BinaryIO, TextIO, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.booster_stats_item import BoosterStatsItem
    from ..models.days_item import DaysItem


T = TypeVar("T", bound="ResponseWithDateType0Item")


@_attrs_define
class ResponseWithDateType0Item:
    """
    Attributes:
        dates (list[datetime.date] | Unset): Dates for which information is to be provided
        views (int | Unset): Number of views. <br>
            For all days, across all WB articles and platforms
        clicks (int | Unset): Number of clicks.<br>
            For all days, across all WB articles and platforms
        ctr (float | Unset): Clickability metric.<br>
            The ratio of clicks to displays. Expressed as a percentage<br>
            For all days, across all WB articles and platforms
        cpc (float | Unset): Average cost per click, ₽.<br>
            For all days, across all WB articles and platforms
        sum_ (float | Unset): Expenses, ₽.<br>
            For all days, across all WB articles and platforms
        atbs (int | Unset): Number of products added to the basket.<br>
            For all days, across all WB articles and platforms
        orders (int | Unset): Orders number.<br>
            For all days, across all WB articles and platforms
        cr (float | Unset): CR(conversion rate) is the ratio of the number of orders to the total number of visits to
            the campaign.<br>
            For all days, across all WB articles and platforms
        shks (int | Unset): Number of ordered products, pcs<br>
            For all days, across all WB articles and platforms
        sum_price (float | Unset): Orders amount, ₽.<br>
            For all days, across all WB articles and platforms
        days (list[DaysItem] | Unset): Statistics by days
        booster_stats (list[BoosterStatsItem] | Unset): Statistics on the average position of the product on search
            results pages and catalog pages (for campaigns with standard bid)
        advert_id (int | Unset): Campaign ID
    """

    dates: list[datetime.date] | Unset = UNSET
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
    days: list[DaysItem] | Unset = UNSET
    booster_stats: list[BoosterStatsItem] | Unset = UNSET
    advert_id: int | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        from ..models.booster_stats_item import BoosterStatsItem
        from ..models.days_item import DaysItem

        dates: list[str] | Unset = UNSET
        if not isinstance(self.dates, Unset):
            dates = []
            for dates_item_data in self.dates:
                dates_item = dates_item_data.isoformat()
                dates.append(dates_item)

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

        days: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.days, Unset):
            days = []
            for componentsschemas_days_item_data in self.days:
                componentsschemas_days_item = componentsschemas_days_item_data.to_dict()
                days.append(componentsschemas_days_item)

        booster_stats: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.booster_stats, Unset):
            booster_stats = []
            for componentsschemas_booster_stats_item_data in self.booster_stats:
                componentsschemas_booster_stats_item = (
                    componentsschemas_booster_stats_item_data.to_dict()
                )
                booster_stats.append(componentsschemas_booster_stats_item)

        advert_id = self.advert_id

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if dates is not UNSET:
            field_dict["dates"] = dates
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
        if days is not UNSET:
            field_dict["days"] = days
        if booster_stats is not UNSET:
            field_dict["boosterStats"] = booster_stats
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.booster_stats_item import BoosterStatsItem
        from ..models.days_item import DaysItem

        d = dict(src_dict)
        _dates = d.pop("dates", UNSET)
        dates: list[datetime.date] | Unset = UNSET
        if _dates is not UNSET:
            dates = []
            for dates_item_data in _dates:
                dates_item = isoparse(dates_item_data).date()

                dates.append(dates_item)

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

        _days = d.pop("days", UNSET)
        days: list[DaysItem] | Unset = UNSET
        if _days is not UNSET:
            days = []
            for componentsschemas_days_item_data in _days:
                componentsschemas_days_item = DaysItem.from_dict(
                    componentsschemas_days_item_data
                )

                days.append(componentsschemas_days_item)

        _booster_stats = d.pop("boosterStats", UNSET)
        booster_stats: list[BoosterStatsItem] | Unset = UNSET
        if _booster_stats is not UNSET:
            booster_stats = []
            for componentsschemas_booster_stats_item_data in _booster_stats:
                componentsschemas_booster_stats_item = BoosterStatsItem.from_dict(
                    componentsschemas_booster_stats_item_data
                )

                booster_stats.append(componentsschemas_booster_stats_item)

        advert_id = d.pop("advertId", UNSET)

        response_with_date_type_0_item = cls(
            dates=dates,
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
            days=days,
            booster_stats=booster_stats,
            advert_id=advert_id,
        )

        return response_with_date_type_0_item
