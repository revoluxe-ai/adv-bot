import datetime
from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.daily_stats_2_item import DailyStats2Item


T = TypeVar("T", bound="StatsBlok2")


@_attrs_define
class StatsBlok2:
    """
    Attributes:
        item_id (Union[Unset, int]): ID bannera
        item_name (Union[Unset, str]): Brend
        category_name (Union[Unset, str]): Nazvanie kategorii
        advert_type (Union[Unset, int]): <dl> <dt>Tip mediakampanii:</dt> <dd><code>1</code> — razmeschenie po
            dnjam</dd> <dd><code>2</code> — razmeschenie po prosmotram</dd> </dl>
        place (Union[Unset, int]): Mesto na stranitse
        views (Union[Unset, int]): Kolichestvo prosmotrov
        clicks (Union[Unset, int]): Kolichestvo klikov
        cr (Union[Unset, float]): CR(conversion rate) — eto otnoshenie kolichestva zakazov k obschemu kolichestvu
            poseschenij mediakampanii
        ctr (Union[Unset, float]): CTR (click-through rate) — pokazatel' klikabel'nosti, otnoshenie chisla klikov k
            kolichestvu pokazov v ramkah mediakampanii
        date_from (Union[Unset, datetime.datetime]): Vremja nachala razmeschenija
        date_to (Union[Unset, datetime.datetime]): Vremja zavershenija razmeschenija
        subject_name (Union[Unset, str]): Roditel'skaja kategorija predmeta
        atbs (Union[Unset, int]): Kolichestvo dobavlenij tovarov v korzinu
        orders (Union[Unset, int]): Kolichestvo zakazov
        price (Union[Unset, float]): Stoimost' razmeschenija
        cpc (Union[Unset, float]): (cost per click) — tsena klika po prodvigaemomu tovaru
        status (Union[Unset, int]): Status mediakampanii
        daily_stats (Union[Unset, list['DailyStats2Item']]):
        expenses (Union[Unset, float]): Stoimost' razmeschenija bannera
        cr1 (Union[Unset, float]): Otnoshenie kolichestva dobavlenij v korzinu k kolichestvu klikov
        cr2 (Union[Unset, int]): Otnoshenie kolichestva zakazov k kolichestvu dobavlenij v korzinu
    """

    item_id: Union[Unset, int] = UNSET
    item_name: Union[Unset, str] = UNSET
    category_name: Union[Unset, str] = UNSET
    advert_type: Union[Unset, int] = UNSET
    place: Union[Unset, int] = UNSET
    views: Union[Unset, int] = UNSET
    clicks: Union[Unset, int] = UNSET
    cr: Union[Unset, float] = UNSET
    ctr: Union[Unset, float] = UNSET
    date_from: Union[Unset, datetime.datetime] = UNSET
    date_to: Union[Unset, datetime.datetime] = UNSET
    subject_name: Union[Unset, str] = UNSET
    atbs: Union[Unset, int] = UNSET
    orders: Union[Unset, int] = UNSET
    price: Union[Unset, float] = UNSET
    cpc: Union[Unset, float] = UNSET
    status: Union[Unset, int] = UNSET
    daily_stats: Union[Unset, list["DailyStats2Item"]] = UNSET
    expenses: Union[Unset, float] = UNSET
    cr1: Union[Unset, float] = UNSET
    cr2: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        item_id = self.item_id

        item_name = self.item_name

        category_name = self.category_name

        advert_type = self.advert_type

        place = self.place

        views = self.views

        clicks = self.clicks

        cr = self.cr

        ctr = self.ctr

        date_from: Union[Unset, str] = UNSET
        if not isinstance(self.date_from, Unset):
            date_from = self.date_from.isoformat()

        date_to: Union[Unset, str] = UNSET
        if not isinstance(self.date_to, Unset):
            date_to = self.date_to.isoformat()

        subject_name = self.subject_name

        atbs = self.atbs

        orders = self.orders

        price = self.price

        cpc = self.cpc

        status = self.status

        daily_stats: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.daily_stats, Unset):
            daily_stats = []
            for componentsschemas_daily_stats_2_item_data in self.daily_stats:
                componentsschemas_daily_stats_2_item = (
                    componentsschemas_daily_stats_2_item_data.to_dict()
                )
                daily_stats.append(componentsschemas_daily_stats_2_item)

        expenses = self.expenses

        cr1 = self.cr1

        cr2 = self.cr2

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if item_id is not UNSET:
            field_dict["item_id"] = item_id
        if item_name is not UNSET:
            field_dict["item_name"] = item_name
        if category_name is not UNSET:
            field_dict["category_name"] = category_name
        if advert_type is not UNSET:
            field_dict["advert_type"] = advert_type
        if place is not UNSET:
            field_dict["place"] = place
        if views is not UNSET:
            field_dict["views"] = views
        if clicks is not UNSET:
            field_dict["clicks"] = clicks
        if cr is not UNSET:
            field_dict["cr"] = cr
        if ctr is not UNSET:
            field_dict["ctr"] = ctr
        if date_from is not UNSET:
            field_dict["date_from"] = date_from
        if date_to is not UNSET:
            field_dict["date_to"] = date_to
        if subject_name is not UNSET:
            field_dict["subject_name"] = subject_name
        if atbs is not UNSET:
            field_dict["atbs"] = atbs
        if orders is not UNSET:
            field_dict["orders"] = orders
        if price is not UNSET:
            field_dict["price"] = price
        if cpc is not UNSET:
            field_dict["cpc"] = cpc
        if status is not UNSET:
            field_dict["status"] = status
        if daily_stats is not UNSET:
            field_dict["daily_stats"] = daily_stats
        if expenses is not UNSET:
            field_dict["expenses"] = expenses
        if cr1 is not UNSET:
            field_dict["cr1"] = cr1
        if cr2 is not UNSET:
            field_dict["cr2"] = cr2

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.daily_stats_2_item import DailyStats2Item

        d = dict(src_dict)
        item_id = d.pop("item_id", UNSET)

        item_name = d.pop("item_name", UNSET)

        category_name = d.pop("category_name", UNSET)

        advert_type = d.pop("advert_type", UNSET)

        place = d.pop("place", UNSET)

        views = d.pop("views", UNSET)

        clicks = d.pop("clicks", UNSET)

        cr = d.pop("cr", UNSET)

        ctr = d.pop("ctr", UNSET)

        _date_from = d.pop("date_from", UNSET)
        date_from: Union[Unset, datetime.datetime]
        if isinstance(_date_from, Unset):
            date_from = UNSET
        else:
            date_from = isoparse(_date_from)

        _date_to = d.pop("date_to", UNSET)
        date_to: Union[Unset, datetime.datetime]
        if isinstance(_date_to, Unset):
            date_to = UNSET
        else:
            date_to = isoparse(_date_to)

        subject_name = d.pop("subject_name", UNSET)

        atbs = d.pop("atbs", UNSET)

        orders = d.pop("orders", UNSET)

        price = d.pop("price", UNSET)

        cpc = d.pop("cpc", UNSET)

        status = d.pop("status", UNSET)

        daily_stats = []
        _daily_stats = d.pop("daily_stats", UNSET)
        for componentsschemas_daily_stats_2_item_data in _daily_stats or []:
            componentsschemas_daily_stats_2_item = DailyStats2Item.from_dict(
                componentsschemas_daily_stats_2_item_data
            )

            daily_stats.append(componentsschemas_daily_stats_2_item)

        expenses = d.pop("expenses", UNSET)

        cr1 = d.pop("cr1", UNSET)

        cr2 = d.pop("cr2", UNSET)

        stats_blok_2 = cls(
            item_id=item_id,
            item_name=item_name,
            category_name=category_name,
            advert_type=advert_type,
            place=place,
            views=views,
            clicks=clicks,
            cr=cr,
            ctr=ctr,
            date_from=date_from,
            date_to=date_to,
            subject_name=subject_name,
            atbs=atbs,
            orders=orders,
            price=price,
            cpc=cpc,
            status=status,
            daily_stats=daily_stats,
            expenses=expenses,
            cr1=cr1,
            cr2=cr2,
        )

        stats_blok_2.additional_properties = d
        return stats_blok_2

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
