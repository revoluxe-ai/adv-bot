from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="FullStatsItem")


@_attrs_define
class FullStatsItem:
    """Statistika po odnoj kampanii za period, ukazannyj v zaprose. Po vsem artikulam WB i platformam

    Attributes:
        advert_id (int): ID kampanii
        atbs (int): Kolichestvo dobavlenij tovarov v korzinu
        canceled (int): Otmeny, sht.
        clicks (int): Kolichestvo klikov
        cpc (float): Srednjaja stoimost' klika, ₽
        cr (float): CR (conversion rate) — otnoshenie kolichestva zakazov k obschemu kolichestvu klikov
        ctr (float): CTR (click-through rate) — otnoshenie chisla klikov k kolichestvu pokazov v protsentah
        days (Any): Statistka po dnjam
        orders (int): Kolichestvo zakazov
        shks (int): Kolichestvo zakazannyh tovarov, sht.
        sum_ (float): Zatraty, ₽
        sum_price (float): Summa zakazov, ₽
        views (int): Kolichestvo prosmotrov
        booster_stats (Any | Unset): Statistika po srednej pozitsii tovara (dlja kampanij s edinoj stavkoj)
    """

    advert_id: int
    atbs: int
    canceled: int
    clicks: int
    cpc: float
    cr: float
    ctr: float
    days: Any
    orders: int
    shks: int
    sum_: float
    sum_price: float
    views: int
    booster_stats: Any | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        advert_id = self.advert_id

        atbs = self.atbs

        canceled = self.canceled

        clicks = self.clicks

        cpc = self.cpc

        cr = self.cr

        ctr = self.ctr

        days = self.days

        orders = self.orders

        shks = self.shks

        sum_ = self.sum_

        sum_price = self.sum_price

        views = self.views

        booster_stats = self.booster_stats

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "advertId": advert_id,
                "atbs": atbs,
                "canceled": canceled,
                "clicks": clicks,
                "cpc": cpc,
                "cr": cr,
                "ctr": ctr,
                "days": days,
                "orders": orders,
                "shks": shks,
                "sum": sum_,
                "sum_price": sum_price,
                "views": views,
            }
        )
        if booster_stats is not UNSET:
            field_dict["boosterStats"] = booster_stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        advert_id = d.pop("advertId")

        atbs = d.pop("atbs")

        canceled = d.pop("canceled")

        clicks = d.pop("clicks")

        cpc = d.pop("cpc")

        cr = d.pop("cr")

        ctr = d.pop("ctr")

        days = d.pop("days")

        orders = d.pop("orders")

        shks = d.pop("shks")

        sum_ = d.pop("sum")

        sum_price = d.pop("sum_price")

        views = d.pop("views")

        booster_stats = d.pop("boosterStats", UNSET)

        full_stats_item = cls(
            advert_id=advert_id,
            atbs=atbs,
            canceled=canceled,
            clicks=clicks,
            cpc=cpc,
            cr=cr,
            ctr=ctr,
            days=days,
            orders=orders,
            shks=shks,
            sum_=sum_,
            sum_price=sum_price,
            views=views,
            booster_stats=booster_stats,
        )

        full_stats_item.additional_properties = d
        return full_stats_item

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
