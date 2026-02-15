from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="FullStatsItem")


@_attrs_define
class FullStatsItem:
    """Statistics for a single campaign for the period specified in the request. For all WB articles and platforms

    Attributes:
        advert_id (int): Campaign ID
        atbs (int): Number of products added to the cart
        canceled (int): Cancellations, pcs
        clicks (int): Number of clicks
        cpc (float): Average cost per click, ₽
        cr (float): CR (conversion rate) — the ratio of the number of orders to the total number of clicks
        ctr (float): CTR (click-through rate) — the ratio of clicks to displays, expressed as a percentage
        days (Any): Statistics by days
        orders (int): Number of orders
        shks (int): Number of ordered products, pcs
        sum_ (float): Costs, ₽
        sum_price (float): Orders amount, ₽
        views (int): Number of views
        booster_stats (Union[Unset, Any]): Statistics on the average position (for campaigns with standard bid)
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
    booster_stats: Union[Unset, Any] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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

        field_dict: Dict[str, Any] = {}
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
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
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
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
