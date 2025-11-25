from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.product_orders_metrics import ProductOrdersMetrics
    from ..models.product_orders_text_item import ProductOrdersTextItem


T = TypeVar("T", bound="ProductOrdersResponse")


@_attrs_define
class ProductOrdersResponse:
    """
    Attributes:
        total (List['ProductOrdersMetrics']): Itog po tovaram
        items (List['ProductOrdersTextItem']): Elementy tablitsy
    """

    total: List["ProductOrdersMetrics"]
    items: List["ProductOrdersTextItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        total = []
        for total_item_data in self.total:
            total_item = total_item_data.to_dict()
            total.append(total_item)

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "total": total,
                "items": items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.product_orders_metrics import ProductOrdersMetrics
        from ..models.product_orders_text_item import ProductOrdersTextItem

        d = src_dict.copy()
        total = []
        _total = d.pop("total")
        for total_item_data in _total:
            total_item = ProductOrdersMetrics.from_dict(total_item_data)

            total.append(total_item)

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = ProductOrdersTextItem.from_dict(items_item_data)

            items.append(items_item)

        product_orders_response = cls(
            total=total,
            items=items,
        )

        product_orders_response.additional_properties = d
        return product_orders_response

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
