from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.booster_stats_item import BoosterStatsItem
    from ..models.days_item import DaysItem
    from ..models.response_with_interval_item_interval import (
        ResponseWithIntervalItemInterval,
    )


T = TypeVar("T", bound="ResponseWithIntervalItem")


@_attrs_define
class ResponseWithIntervalItem:
    """
    Attributes:
        interval (ResponseWithIntervalItemInterval | Unset): Period
        views (int | Unset): Kolichestvo prosmotrov. <br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        clicks (int | Unset): Kolichestvo klikov.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        ctr (float | Unset): Pokazatel' klikabel'nosti.<br>
            Otnoshenie chisla klikov k kolichestvu pokazov. Vyrazhaetsja v protsentah.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        cpc (float | Unset): Srednjaja stoimost' klika, ₽.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        sum_ (float | Unset): Zatraty, ₽.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        atbs (int | Unset): Kolichestvo dobavlenij tovarov v korzinu.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        orders (int | Unset): Kolichestvo zakazov.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        cr (float | Unset): CR(conversion rate) — eto otnoshenie kolichestva zakazov k obschemu kolichestvu poseschenij
            kampanii.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        shks (int | Unset): Kolichestvo zakazannyh tovarov, sht.<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        sum_price (float | Unset): Zakazov na summu, ₽<br>
            Za vse dni zaproshennogo diapazona, po vsem artikulam WB i platformam
        days (list[DaysItem] | Unset): Statistka po dnjam
        booster_stats (list[BoosterStatsItem] | Unset): Statistika po srednej pozitsii tovara na stranitsah poiskovoj
            vydachi i kataloga (dlja kampanij s edinoj stavkoj)
        advert_id (int | Unset): ID kampanii
    """

    interval: ResponseWithIntervalItemInterval | Unset = UNSET
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
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        interval: dict[str, Any] | Unset = UNSET
        if not isinstance(self.interval, Unset):
            interval = self.interval.to_dict()

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
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if interval is not UNSET:
            field_dict["interval"] = interval
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
        from ..models.response_with_interval_item_interval import (
            ResponseWithIntervalItemInterval,
        )

        d = dict(src_dict)
        _interval = d.pop("interval", UNSET)
        interval: ResponseWithIntervalItemInterval | Unset
        if isinstance(_interval, Unset):
            interval = UNSET
        else:
            interval = ResponseWithIntervalItemInterval.from_dict(_interval)

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

        response_with_interval_item = cls(
            interval=interval,
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

        response_with_interval_item.additional_properties = d
        return response_with_interval_item

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
