import datetime
from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
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
        dates (Union[Unset, list[datetime.date]]): Daty, za kotorye nuzhno poluchit' informatsiju
        views (Union[Unset, int]): Kolichestvo prosmotrov. <br>
            Za vse dni, po vsem artikulam WB i platformam
        clicks (Union[Unset, int]): Kolichestvo klikov.<br>
            Za vse dni, po vsem artikulam WB i platformam
        ctr (Union[Unset, float]): Pokazatel' klikabel'nosti.<br>
            Otnoshenie chisla klikov k kolichestvu pokazov. Vyrazhaetsja v protsentah<br>
            Za vse dni, po vsem artikulam WB i platformam<br>
        cpc (Union[Unset, float]): Srednjaja stoimost' klika, ₽.<br>
            Za vse dni, po vsem artikulam WB i platformam
        sum_ (Union[Unset, float]): Zatraty, ₽.<br>
            Za vse dni, po vsem artikulam WB i platformam
        atbs (Union[Unset, int]): Kolichestvo dobavlenij tovarov v korzinu.<br>
            Za vse dni, po vsem artikulam WB i platformam
        orders (Union[Unset, int]): Kolichestvo zakazov.<br>
            Za vse dni, po vsem artikulam WB i platformam
        cr (Union[Unset, float]): CR(conversion rate) — eto otnoshenie kolichestva zakazov k obschemu kolichestvu
            poseschenij kampanii.<br>
            Za vse dni, po vsem artikulam WB i platformam
        shks (Union[Unset, int]): Kolichestvo zakazannyh tovarov, sht.<br>
            Za vse dni, po vsem artikulam WB i platformam
        sum_price (Union[Unset, float]): Zakazov na summu, ₽<br>
            Za vse dni, po vsem artikulam WB i platformam
        days (Union[Unset, list['DaysItem']]): Statistka po dnjam
        booster_stats (Union[Unset, list['BoosterStatsItem']]): Statistika po srednej pozitsii tovara na stranitsah
            poiskovoj vydachi i kataloga (dlja kampanij s edinoj stavkoj)
        advert_id (Union[Unset, int]): ID kampanii
    """

    dates: Union[Unset, list[datetime.date]] = UNSET
    views: Union[Unset, int] = UNSET
    clicks: Union[Unset, int] = UNSET
    ctr: Union[Unset, float] = UNSET
    cpc: Union[Unset, float] = UNSET
    sum_: Union[Unset, float] = UNSET
    atbs: Union[Unset, int] = UNSET
    orders: Union[Unset, int] = UNSET
    cr: Union[Unset, float] = UNSET
    shks: Union[Unset, int] = UNSET
    sum_price: Union[Unset, float] = UNSET
    days: Union[Unset, list["DaysItem"]] = UNSET
    booster_stats: Union[Unset, list["BoosterStatsItem"]] = UNSET
    advert_id: Union[Unset, int] = UNSET

    def to_dict(self) -> dict[str, Any]:
        dates: Union[Unset, list[str]] = UNSET
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

        days: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.days, Unset):
            days = []
            for componentsschemas_days_item_data in self.days:
                componentsschemas_days_item = componentsschemas_days_item_data.to_dict()
                days.append(componentsschemas_days_item)

        booster_stats: Union[Unset, list[dict[str, Any]]] = UNSET
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
        dates = []
        _dates = d.pop("dates", UNSET)
        for dates_item_data in _dates or []:
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

        days = []
        _days = d.pop("days", UNSET)
        for componentsschemas_days_item_data in _days or []:
            componentsschemas_days_item = DaysItem.from_dict(
                componentsschemas_days_item_data
            )

            days.append(componentsschemas_days_item)

        booster_stats = []
        _booster_stats = d.pop("boosterStats", UNSET)
        for componentsschemas_booster_stats_item_data in _booster_stats or []:
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
