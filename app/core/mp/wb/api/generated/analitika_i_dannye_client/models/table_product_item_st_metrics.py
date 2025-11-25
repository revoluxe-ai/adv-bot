from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.table_product_item_st_metrics_availability import TableProductItemStMetricsAvailability

if TYPE_CHECKING:
    from ..models.float_graph_by_period_item import FloatGraphByPeriodItem
    from ..models.table_common_metrics_avg_stock_turnover import TableCommonMetricsAvgStockTurnover
    from ..models.table_common_metrics_office_missing_time import TableCommonMetricsOfficeMissingTime
    from ..models.table_common_metrics_sale_rate import TableCommonMetricsSaleRate
    from ..models.table_product_item_st_metrics_current_price import TableProductItemStMetricsCurrentPrice


T = TypeVar("T", bound="TableProductItemStMetrics")


@_attrs_define
class TableProductItemStMetrics:
    """Metriki tovara

    Attributes:
        orders_count (int): Zakazy, sht. Example: 100.
        orders_sum (int): Zakazy, summa Example: 100000.
        avg_orders (float): Srednee kolichestvo zakazov v den' Example: 200.
        avg_orders_by_month (List['FloatGraphByPeriodItem']): Srednee kolichestvo zakazov po mesjatsam
        buyout_count (int): Vykupy, sht. Example: 150.
        buyout_sum (int): Vykupy, summa Example: 150000.
        buyout_percent (int): Protsent vykupa Example: 5.
        stock_count (int): Ostatki na tekuschij den', sht. Example: 50.
        stock_sum (int): Stoimost' ostatkov na tekuschij den' Example: 50000.
        sale_rate (TableCommonMetricsSaleRate): Oborachivaemost' tekuschih ostatkov. Osobye sluchai:
              1. `"hours":-1` — beskonechnaja dlitel'nost'
              2. `"hours":-2` — nulevaja dlitel'nost'
              3. `"hours":-3` — nerasschitannaja dlitel'nost'
        avg_stock_turnover (TableCommonMetricsAvgStockTurnover): Oborachivaemost' srednih ostatkov. Osobye sluchai:
              1. `"hours":-1` — beskonechnaja dlitel'nost'
              2. `"hours":-2` — nulevaja dlitel'nost'
              3. `"hours":-3` — nerasschitannaja dlitel'nost'
        to_client_count (int): V puti k klientu, sht. Example: 20.
        from_client_count (int): V puti ot klienta, sht. Example: 30.
        office_missing_time (TableCommonMetricsOfficeMissingTime): Vremja otsutstvija tovara na sklade. Osobye sluchai:
              1. `"hours":-1` — beskonechnaja dlitel'nost'
              2. `"hours":-2` — nulevaja dlitel'nost'
              3. `"hours":-3` — nerasschitannaja dlitel'nost'
              4. `"hours":-4` — otsutstvie v techenie vsego perioda
        lost_orders_count (float): Upuschennye zakazy, sht. Osobye sluchai:
              1. Znachenie men'she `0` i ne ravno `-2` — znachenie ne rasschitano
              2. Znachenie `-2` — nulevoe znachenie
             Example: 1550.52.
        lost_orders_sum (float): Upuschennye zakazy, summa. Osobye sluchai:
              1. Znachenie men'she `0` i ne ravno `-2` — znachenie ne rasschitano
              2. Znachenie `-2` — nulevoe znachenie
             Example: 155000.25.
        lost_buyouts_count (float): Upuschennye vykupy, sht. Osobye sluchai:
              1. Znachenie men'she `0` i ne ravno `-2` — znachenie ne rasschitano
              2. Znachenie `-2` — nulevoe znachenie
             Example: 123.55.
        lost_buyouts_sum (float): Upuschennye vykupy, summa. Osobye sluchai:
              1. Znachenie men'she `0` i ne ravno `-2` — znachenie ne rasschitano
              2. Znachenie `-2` — nulevoe znachenie
             Example: 225555.15.
        current_price (TableProductItemStMetricsCurrentPrice): Tekuschaja tsena
        availability (TableProductItemStMetricsAvailability): Dostupnost' tovara:
              - `deficient` — Defitsit
              - `actual` — Aktual'nyj
              - `balanced` — Balans
              - `nonActual` — Neaktual'nyj
              - `nonLiquid` — Nelikvid
              - `invalidData` — Ne rasschitano
             Example: deficient.
    """

    orders_count: int
    orders_sum: int
    avg_orders: float
    avg_orders_by_month: List["FloatGraphByPeriodItem"]
    buyout_count: int
    buyout_sum: int
    buyout_percent: int
    stock_count: int
    stock_sum: int
    sale_rate: "TableCommonMetricsSaleRate"
    avg_stock_turnover: "TableCommonMetricsAvgStockTurnover"
    to_client_count: int
    from_client_count: int
    office_missing_time: "TableCommonMetricsOfficeMissingTime"
    lost_orders_count: float
    lost_orders_sum: float
    lost_buyouts_count: float
    lost_buyouts_sum: float
    current_price: "TableProductItemStMetricsCurrentPrice"
    availability: TableProductItemStMetricsAvailability
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        orders_count = self.orders_count

        orders_sum = self.orders_sum

        avg_orders = self.avg_orders

        avg_orders_by_month = []
        for avg_orders_by_month_item_data in self.avg_orders_by_month:
            avg_orders_by_month_item = avg_orders_by_month_item_data.to_dict()
            avg_orders_by_month.append(avg_orders_by_month_item)

        buyout_count = self.buyout_count

        buyout_sum = self.buyout_sum

        buyout_percent = self.buyout_percent

        stock_count = self.stock_count

        stock_sum = self.stock_sum

        sale_rate = self.sale_rate.to_dict()

        avg_stock_turnover = self.avg_stock_turnover.to_dict()

        to_client_count = self.to_client_count

        from_client_count = self.from_client_count

        office_missing_time = self.office_missing_time.to_dict()

        lost_orders_count = self.lost_orders_count

        lost_orders_sum = self.lost_orders_sum

        lost_buyouts_count = self.lost_buyouts_count

        lost_buyouts_sum = self.lost_buyouts_sum

        current_price = self.current_price.to_dict()

        availability = self.availability.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "ordersCount": orders_count,
                "ordersSum": orders_sum,
                "avgOrders": avg_orders,
                "avgOrdersByMonth": avg_orders_by_month,
                "buyoutCount": buyout_count,
                "buyoutSum": buyout_sum,
                "buyoutPercent": buyout_percent,
                "stockCount": stock_count,
                "stockSum": stock_sum,
                "saleRate": sale_rate,
                "avgStockTurnover": avg_stock_turnover,
                "toClientCount": to_client_count,
                "fromClientCount": from_client_count,
                "officeMissingTime": office_missing_time,
                "lostOrdersCount": lost_orders_count,
                "lostOrdersSum": lost_orders_sum,
                "lostBuyoutsCount": lost_buyouts_count,
                "lostBuyoutsSum": lost_buyouts_sum,
                "currentPrice": current_price,
                "availability": availability,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.float_graph_by_period_item import FloatGraphByPeriodItem
        from ..models.table_common_metrics_avg_stock_turnover import TableCommonMetricsAvgStockTurnover
        from ..models.table_common_metrics_office_missing_time import TableCommonMetricsOfficeMissingTime
        from ..models.table_common_metrics_sale_rate import TableCommonMetricsSaleRate
        from ..models.table_product_item_st_metrics_current_price import TableProductItemStMetricsCurrentPrice

        d = src_dict.copy()
        orders_count = d.pop("ordersCount")

        orders_sum = d.pop("ordersSum")

        avg_orders = d.pop("avgOrders")

        avg_orders_by_month = []
        _avg_orders_by_month = d.pop("avgOrdersByMonth")
        for avg_orders_by_month_item_data in _avg_orders_by_month:
            avg_orders_by_month_item = FloatGraphByPeriodItem.from_dict(avg_orders_by_month_item_data)

            avg_orders_by_month.append(avg_orders_by_month_item)

        buyout_count = d.pop("buyoutCount")

        buyout_sum = d.pop("buyoutSum")

        buyout_percent = d.pop("buyoutPercent")

        stock_count = d.pop("stockCount")

        stock_sum = d.pop("stockSum")

        sale_rate = TableCommonMetricsSaleRate.from_dict(d.pop("saleRate"))

        avg_stock_turnover = TableCommonMetricsAvgStockTurnover.from_dict(d.pop("avgStockTurnover"))

        to_client_count = d.pop("toClientCount")

        from_client_count = d.pop("fromClientCount")

        office_missing_time = TableCommonMetricsOfficeMissingTime.from_dict(d.pop("officeMissingTime"))

        lost_orders_count = d.pop("lostOrdersCount")

        lost_orders_sum = d.pop("lostOrdersSum")

        lost_buyouts_count = d.pop("lostBuyoutsCount")

        lost_buyouts_sum = d.pop("lostBuyoutsSum")

        current_price = TableProductItemStMetricsCurrentPrice.from_dict(d.pop("currentPrice"))

        availability = TableProductItemStMetricsAvailability(d.pop("availability"))

        table_product_item_st_metrics = cls(
            orders_count=orders_count,
            orders_sum=orders_sum,
            avg_orders=avg_orders,
            avg_orders_by_month=avg_orders_by_month,
            buyout_count=buyout_count,
            buyout_sum=buyout_sum,
            buyout_percent=buyout_percent,
            stock_count=stock_count,
            stock_sum=stock_sum,
            sale_rate=sale_rate,
            avg_stock_turnover=avg_stock_turnover,
            to_client_count=to_client_count,
            from_client_count=from_client_count,
            office_missing_time=office_missing_time,
            lost_orders_count=lost_orders_count,
            lost_orders_sum=lost_orders_sum,
            lost_buyouts_count=lost_buyouts_count,
            lost_buyouts_sum=lost_buyouts_sum,
            current_price=current_price,
            availability=availability,
        )

        table_product_item_st_metrics.additional_properties = d
        return table_product_item_st_metrics

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
