import datetime
from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

T = TypeVar("T", bound="ProductOrdersMetrics")


@_attrs_define
class ProductOrdersMetrics:
    """
    Attributes:
        dt (datetime.date): Data sbora statistiki Example: 2024-02-10.
        avg_position (int): Srednjaja pozitsija tovara v rezul'tatah poiska Example: 10.
        orders (int): Skol'ko raz tovary iz poiska zakazali Example: 20.
    """

    dt: datetime.date
    avg_position: int
    orders: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        dt = self.dt.isoformat()

        avg_position = self.avg_position

        orders = self.orders

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "dt": dt,
                "avgPosition": avg_position,
                "orders": orders,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        dt = isoparse(d.pop("dt")).date()

        avg_position = d.pop("avgPosition")

        orders = d.pop("orders")

        product_orders_metrics = cls(
            dt=dt,
            avg_position=avg_position,
            orders=orders,
        )

        product_orders_metrics.additional_properties = d
        return product_orders_metrics

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
