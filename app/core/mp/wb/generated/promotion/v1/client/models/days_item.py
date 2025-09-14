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
    from ..models.days_item_apps_item import DaysItemAppsItem


T = TypeVar("T", bound="DaysItem")


@_attrs_define
class DaysItem:
    """
    Attributes:
        date (Union[Unset, datetime.datetime]): Data, za kotoruju predstavleny dannye
        views (Union[Unset, int]): Kolichestvo prosmotrov
        clicks (Union[Unset, int]): Kolichestvo klikov
        ctr (Union[Unset, float]): Pokazatel' klikabel'nosti, otnoshenie chisla klikov k kolichestvu pokazov, %
        cpc (Union[Unset, float]): Srednjaja stoimost' klika, ₽
        sum_ (Union[Unset, float]): Zatraty, ₽
        atbs (Union[Unset, int]): Kolichestvo dobavlenij tovarov v korzinu
        orders (Union[Unset, int]): Kolichestvo zakazov
        cr (Union[Unset, float]): CR(conversion rate) — otnoshenie kolichestva zakazov k obschemu kolichestvu
            poseschenij kampanii
        shks (Union[Unset, int]): Kolichestvo zakazannyh tovarov, sht.
        sum_price (Union[Unset, float]): Zakazov na summu, ₽
        apps (Union[Unset, list['DaysItemAppsItem']]): Blok informatsii o platforme
    """

    date: Union[Unset, datetime.datetime] = UNSET
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
    apps: Union[Unset, list["DaysItemAppsItem"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        date: Union[Unset, str] = UNSET
        if not isinstance(self.date, Unset):
            date = self.date.isoformat()

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

        apps: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.apps, Unset):
            apps = []
            for apps_item_data in self.apps:
                apps_item = apps_item_data.to_dict()
                apps.append(apps_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if date is not UNSET:
            field_dict["date"] = date
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
        if apps is not UNSET:
            field_dict["apps"] = apps

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.days_item_apps_item import DaysItemAppsItem

        d = dict(src_dict)
        _date = d.pop("date", UNSET)
        date: Union[Unset, datetime.datetime]
        if isinstance(_date, Unset):
            date = UNSET
        else:
            date = isoparse(_date)

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

        apps = []
        _apps = d.pop("apps", UNSET)
        for apps_item_data in _apps or []:
            apps_item = DaysItemAppsItem.from_dict(apps_item_data)

            apps.append(apps_item)

        days_item = cls(
            date=date,
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
            apps=apps,
        )

        days_item.additional_properties = d
        return days_item

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
