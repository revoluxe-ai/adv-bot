from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.statistic_conversions import StatisticConversions
    from ..models.statistic_period import StatisticPeriod
    from ..models.statistic_time_to_ready import StatisticTimeToReady
    from ..models.statistic_wb_club import StatisticWbClub


T = TypeVar("T", bound="Statistic")


@_attrs_define
class Statistic:
    """
    Attributes:
        period (StatisticPeriod):
        open_count (int): Kolichestvo perehodov v kartochku tovara Example: 45.
        cart_count (int): Polozhili v korzinu, sht. Example: 34.
        order_count (int): Zakazali tovarov, sht. Example: 19.
        order_sum (int): Zakazali na summu Example: 1262.
        buyout_count (int): Vykupili tovarov, sht. Example: 19.
        buyout_sum (int): Vykupili na summu Example: 1262.
        cancel_count (int): Otmenili tovarov, sht.
        cancel_sum (int): Otmenili na summu
        avg_price (int): Srednjaja tsena Example: 1262.
        avg_orders_count_per_day (float): Srednee kolichestvo zakazov v den', sht. Example: 0.04.
        share_order_percent (float): Dolja v vyruchke Example: 3.
        add_to_wishlist (int): Dobavili v **Otlozhennye** Example: 455.
        time_to_ready (StatisticTimeToReady):
        localization_percent (int): Lokal'nye zakazy v ramkah odnogo regiona Example: 46.
        wb_club (StatisticWbClub):
        conversions (StatisticConversions):
    """

    period: "StatisticPeriod"
    open_count: int
    cart_count: int
    order_count: int
    order_sum: int
    buyout_count: int
    buyout_sum: int
    cancel_count: int
    cancel_sum: int
    avg_price: int
    avg_orders_count_per_day: float
    share_order_percent: float
    add_to_wishlist: int
    time_to_ready: "StatisticTimeToReady"
    localization_percent: int
    wb_club: "StatisticWbClub"
    conversions: "StatisticConversions"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        period = self.period.to_dict()

        open_count = self.open_count

        cart_count = self.cart_count

        order_count = self.order_count

        order_sum = self.order_sum

        buyout_count = self.buyout_count

        buyout_sum = self.buyout_sum

        cancel_count = self.cancel_count

        cancel_sum = self.cancel_sum

        avg_price = self.avg_price

        avg_orders_count_per_day = self.avg_orders_count_per_day

        share_order_percent = self.share_order_percent

        add_to_wishlist = self.add_to_wishlist

        time_to_ready = self.time_to_ready.to_dict()

        localization_percent = self.localization_percent

        wb_club = self.wb_club.to_dict()

        conversions = self.conversions.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "period": period,
                "openCount": open_count,
                "cartCount": cart_count,
                "orderCount": order_count,
                "orderSum": order_sum,
                "buyoutCount": buyout_count,
                "buyoutSum": buyout_sum,
                "cancelCount": cancel_count,
                "cancelSum": cancel_sum,
                "avgPrice": avg_price,
                "avgOrdersCountPerDay": avg_orders_count_per_day,
                "shareOrderPercent": share_order_percent,
                "addToWishlist": add_to_wishlist,
                "timeToReady": time_to_ready,
                "localizationPercent": localization_percent,
                "wbClub": wb_club,
                "conversions": conversions,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.statistic_conversions import StatisticConversions
        from ..models.statistic_period import StatisticPeriod
        from ..models.statistic_time_to_ready import StatisticTimeToReady
        from ..models.statistic_wb_club import StatisticWbClub

        d = src_dict.copy()
        period = StatisticPeriod.from_dict(d.pop("period"))

        open_count = d.pop("openCount")

        cart_count = d.pop("cartCount")

        order_count = d.pop("orderCount")

        order_sum = d.pop("orderSum")

        buyout_count = d.pop("buyoutCount")

        buyout_sum = d.pop("buyoutSum")

        cancel_count = d.pop("cancelCount")

        cancel_sum = d.pop("cancelSum")

        avg_price = d.pop("avgPrice")

        avg_orders_count_per_day = d.pop("avgOrdersCountPerDay")

        share_order_percent = d.pop("shareOrderPercent")

        add_to_wishlist = d.pop("addToWishlist")

        time_to_ready = StatisticTimeToReady.from_dict(d.pop("timeToReady"))

        localization_percent = d.pop("localizationPercent")

        wb_club = StatisticWbClub.from_dict(d.pop("wbClub"))

        conversions = StatisticConversions.from_dict(d.pop("conversions"))

        statistic = cls(
            period=period,
            open_count=open_count,
            cart_count=cart_count,
            order_count=order_count,
            order_sum=order_sum,
            buyout_count=buyout_count,
            buyout_sum=buyout_sum,
            cancel_count=cancel_count,
            cancel_sum=cancel_sum,
            avg_price=avg_price,
            avg_orders_count_per_day=avg_orders_count_per_day,
            share_order_percent=share_order_percent,
            add_to_wishlist=add_to_wishlist,
            time_to_ready=time_to_ready,
            localization_percent=localization_percent,
            wb_club=wb_club,
            conversions=conversions,
        )

        statistic.additional_properties = d
        return statistic

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
