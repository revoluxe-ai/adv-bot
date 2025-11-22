from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="WbClubMetrics")


@_attrs_define
class WbClubMetrics:
    """
    Attributes:
        order_count (int): Zakazali tovarov s WB Klubom, sht. Example: 19.
        order_sum (int): Zakazali na summu s WB Klubom Example: 1262.
        buyout_sum (int): Vykupili na summu s WB Klubom Example: 1262.
        buyout_count (int): Vykupili tovarov s WB Klubom, sht. Example: 19.
        cancel_sum (int): Otmenili na summu s WB Klubom
        cancel_count (int): Otmenili tovarov s WB Klubom, sht.
        avg_price (int): Srednjaja tsena s WB Klubom Example: 1262.
        buyout_percent (int): Protsent vykupa s WB Klubom Example: 43.
        avg_order_count_per_day (float): Srednee kolichestvo zakazov v den' s WB Klubom, sht. Example: 0.04.
    """

    order_count: int
    order_sum: int
    buyout_sum: int
    buyout_count: int
    cancel_sum: int
    cancel_count: int
    avg_price: int
    buyout_percent: int
    avg_order_count_per_day: float
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        order_count = self.order_count

        order_sum = self.order_sum

        buyout_sum = self.buyout_sum

        buyout_count = self.buyout_count

        cancel_sum = self.cancel_sum

        cancel_count = self.cancel_count

        avg_price = self.avg_price

        buyout_percent = self.buyout_percent

        avg_order_count_per_day = self.avg_order_count_per_day

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "orderCount": order_count,
                "orderSum": order_sum,
                "buyoutSum": buyout_sum,
                "buyoutCount": buyout_count,
                "cancelSum": cancel_sum,
                "cancelCount": cancel_count,
                "avgPrice": avg_price,
                "buyoutPercent": buyout_percent,
                "avgOrderCountPerDay": avg_order_count_per_day,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        order_count = d.pop("orderCount")

        order_sum = d.pop("orderSum")

        buyout_sum = d.pop("buyoutSum")

        buyout_count = d.pop("buyoutCount")

        cancel_sum = d.pop("cancelSum")

        cancel_count = d.pop("cancelCount")

        avg_price = d.pop("avgPrice")

        buyout_percent = d.pop("buyoutPercent")

        avg_order_count_per_day = d.pop("avgOrderCountPerDay")

        wb_club_metrics = cls(
            order_count=order_count,
            order_sum=order_sum,
            buyout_sum=buyout_sum,
            buyout_count=buyout_count,
            cancel_sum=cancel_sum,
            cancel_count=cancel_count,
            avg_price=avg_price,
            buyout_percent=buyout_percent,
            avg_order_count_per_day=avg_order_count_per_day,
        )

        wb_club_metrics.additional_properties = d
        return wb_club_metrics

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
