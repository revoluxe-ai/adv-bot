from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_group_item_metrics_add_to_cart import TableGroupItemMetricsAddToCart
    from ..models.table_group_item_metrics_avg_position import TableGroupItemMetricsAvgPosition
    from ..models.table_group_item_metrics_cart_to_order import TableGroupItemMetricsCartToOrder
    from ..models.table_group_item_metrics_open_card import TableGroupItemMetricsOpenCard
    from ..models.table_group_item_metrics_open_to_cart import TableGroupItemMetricsOpenToCart
    from ..models.table_group_item_metrics_orders import TableGroupItemMetricsOrders
    from ..models.table_group_item_metrics_visibility import TableGroupItemMetricsVisibility


T = TypeVar("T", bound="TableGroupItemMetrics")


@_attrs_define
class TableGroupItemMetrics:
    """Metriki tovara v tablitse

    Attributes:
        avg_position (TableGroupItemMetricsAvgPosition): Srednjaja pozitsija tovara v rezul'tatah poiska
        open_card (TableGroupItemMetricsOpenCard): Kolichestvo perehodov v kartochku tovara iz poiska
        add_to_cart (TableGroupItemMetricsAddToCart): Skol'ko raz tovar iz poiska dobavili v korzinu
        open_to_cart (TableGroupItemMetricsOpenToCart): Konversija v korzinu iz poiska — dolja dobavlenij tovara v
            korzinu po otnosheniju ko vsem perehodam v kartochku tovara iz poiska
        orders (TableGroupItemMetricsOrders): Skol'ko raz tovary iz poiska zakazali
        cart_to_order (TableGroupItemMetricsCartToOrder): Konversija v zakaz iz poiska — dolja zakazov tovara po
            otnosheniju ko vsem dobavlenijam tovara iz poiska v korzinu
        visibility (TableGroupItemMetricsVisibility): Protsent vidimosti tovara v rezul'tatah poiska
    """

    avg_position: "TableGroupItemMetricsAvgPosition"
    open_card: "TableGroupItemMetricsOpenCard"
    add_to_cart: "TableGroupItemMetricsAddToCart"
    open_to_cart: "TableGroupItemMetricsOpenToCart"
    orders: "TableGroupItemMetricsOrders"
    cart_to_order: "TableGroupItemMetricsCartToOrder"
    visibility: "TableGroupItemMetricsVisibility"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        avg_position = self.avg_position.to_dict()

        open_card = self.open_card.to_dict()

        add_to_cart = self.add_to_cart.to_dict()

        open_to_cart = self.open_to_cart.to_dict()

        orders = self.orders.to_dict()

        cart_to_order = self.cart_to_order.to_dict()

        visibility = self.visibility.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "avgPosition": avg_position,
                "openCard": open_card,
                "addToCart": add_to_cart,
                "openToCart": open_to_cart,
                "orders": orders,
                "cartToOrder": cart_to_order,
                "visibility": visibility,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_group_item_metrics_add_to_cart import TableGroupItemMetricsAddToCart
        from ..models.table_group_item_metrics_avg_position import TableGroupItemMetricsAvgPosition
        from ..models.table_group_item_metrics_cart_to_order import TableGroupItemMetricsCartToOrder
        from ..models.table_group_item_metrics_open_card import TableGroupItemMetricsOpenCard
        from ..models.table_group_item_metrics_open_to_cart import TableGroupItemMetricsOpenToCart
        from ..models.table_group_item_metrics_orders import TableGroupItemMetricsOrders
        from ..models.table_group_item_metrics_visibility import TableGroupItemMetricsVisibility

        d = src_dict.copy()
        avg_position = TableGroupItemMetricsAvgPosition.from_dict(d.pop("avgPosition"))

        open_card = TableGroupItemMetricsOpenCard.from_dict(d.pop("openCard"))

        add_to_cart = TableGroupItemMetricsAddToCart.from_dict(d.pop("addToCart"))

        open_to_cart = TableGroupItemMetricsOpenToCart.from_dict(d.pop("openToCart"))

        orders = TableGroupItemMetricsOrders.from_dict(d.pop("orders"))

        cart_to_order = TableGroupItemMetricsCartToOrder.from_dict(d.pop("cartToOrder"))

        visibility = TableGroupItemMetricsVisibility.from_dict(d.pop("visibility"))

        table_group_item_metrics = cls(
            avg_position=avg_position,
            open_card=open_card,
            add_to_cart=add_to_cart,
            open_to_cart=open_to_cart,
            orders=orders,
            cart_to_order=cart_to_order,
            visibility=visibility,
        )

        table_group_item_metrics.additional_properties = d
        return table_group_item_metrics

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
