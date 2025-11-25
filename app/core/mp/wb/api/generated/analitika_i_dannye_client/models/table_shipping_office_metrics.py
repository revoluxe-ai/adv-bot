from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_shipping_office_metrics_sale_rate import TableShippingOfficeMetricsSaleRate


T = TypeVar("T", bound="TableShippingOfficeMetrics")


@_attrs_define
class TableShippingOfficeMetrics:
    """Obschie metriki po regionam/skladam otgruzki

    Attributes:
        stock_count (int): Ostatki na tekuschij den', sht. Example: 20.
        stock_sum (int): Ostatki na tekuschij den', summa Example: 20000.
        sale_rate (TableShippingOfficeMetricsSaleRate): Oborachivaemost' tekuschih ostatkov. Osobye sluchai:
              1. `"hours":-1` — beskonechnaja dlitel'nost'
              2. `"hours":-2` — nulevaja dlitel'nost'
              3. `"hours":-3` — nerasschitannaja dlitel'nost'
        to_client_count (int): V puti k klientu, sht. Example: 30.
        from_client_count (int): V puti ot klienta, sht. Example: 40.
    """

    stock_count: int
    stock_sum: int
    sale_rate: "TableShippingOfficeMetricsSaleRate"
    to_client_count: int
    from_client_count: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        stock_count = self.stock_count

        stock_sum = self.stock_sum

        sale_rate = self.sale_rate.to_dict()

        to_client_count = self.to_client_count

        from_client_count = self.from_client_count

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "stockCount": stock_count,
                "stockSum": stock_sum,
                "saleRate": sale_rate,
                "toClientCount": to_client_count,
                "fromClientCount": from_client_count,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_shipping_office_metrics_sale_rate import TableShippingOfficeMetricsSaleRate

        d = src_dict.copy()
        stock_count = d.pop("stockCount")

        stock_sum = d.pop("stockSum")

        sale_rate = TableShippingOfficeMetricsSaleRate.from_dict(d.pop("saleRate"))

        to_client_count = d.pop("toClientCount")

        from_client_count = d.pop("fromClientCount")

        table_shipping_office_metrics = cls(
            stock_count=stock_count,
            stock_sum=stock_sum,
            sale_rate=sale_rate,
            to_client_count=to_client_count,
            from_client_count=from_client_count,
        )

        table_shipping_office_metrics.additional_properties = d
        return table_shipping_office_metrics

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
