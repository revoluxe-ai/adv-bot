import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.daily_stats_1_item import DailyStats1Item


T = TypeVar("T", bound="StatsBlok1")


@_attrs_define
class StatsBlok1:
    """
    Attributes:
        item_id (Union[Unset, int]): Banner ID
        item_name (Union[Unset, str]): Brand
        category_name (Union[Unset, str]): Category name
        advert_type (Union[Unset, int]): Media Campaign Type:
              - `1` — daily placement
              - `2` — views placement
        place (Union[Unset, int]): Placement on the page
        views (Union[Unset, int]): Number of views
        clicks (Union[Unset, int]): Number of clicks
        cr (Union[Unset, float]): CR(conversion rate) is the ratio of the number of orders to the total number of visits
            to the campaign
        ctr (Union[Unset, float]): CTR (click-through rate) — clickability metric, the ratio of the number of clicks to
            the number of displays within a media campaign
        date_from (Union[Unset, datetime.datetime]): The placement start date
        date_to (Union[Unset, datetime.datetime]): The placement stop time
        subject_name (Union[Unset, str]): Parental category of the item
        atbs (Union[Unset, int]): Number of products added to the basket
        orders (Union[Unset, int]): Orders number
        price (Union[Unset, float]): Placement costs
        cpc (Union[Unset, float]): (cost per click) — CPC, click price for the promoted product
        status (Union[Unset, int]): Campaign Status
        daily_stats (Union[Unset, List['DailyStats1Item']]):
        expenses (Union[Unset, float]): Cost of banner placement
        cr1 (Union[Unset, float]): Ratio of the number of additions to basket to the number of clicks
        cr2 (Union[Unset, int]): Ratio of the number of orders to the number of additions to basket
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
    daily_stats: Union[Unset, List["DailyStats1Item"]] = UNSET
    expenses: Union[Unset, float] = UNSET
    cr1: Union[Unset, float] = UNSET
    cr2: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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

        daily_stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.daily_stats, Unset):
            daily_stats = []
            for componentsschemas_daily_stats_1_item_data in self.daily_stats:
                componentsschemas_daily_stats_1_item = (
                    componentsschemas_daily_stats_1_item_data.to_dict()
                )
                daily_stats.append(componentsschemas_daily_stats_1_item)

        expenses = self.expenses

        cr1 = self.cr1

        cr2 = self.cr2

        field_dict: Dict[str, Any] = {}
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
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.daily_stats_1_item import DailyStats1Item

        d = src_dict.copy()
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
        for componentsschemas_daily_stats_1_item_data in _daily_stats or []:
            componentsschemas_daily_stats_1_item = DailyStats1Item.from_dict(
                componentsschemas_daily_stats_1_item_data
            )

            daily_stats.append(componentsschemas_daily_stats_1_item)

        expenses = d.pop("expenses", UNSET)

        cr1 = d.pop("cr1", UNSET)

        cr2 = d.pop("cr2", UNSET)

        stats_blok_1 = cls(
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

        stats_blok_1.additional_properties = d
        return stats_blok_1

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
