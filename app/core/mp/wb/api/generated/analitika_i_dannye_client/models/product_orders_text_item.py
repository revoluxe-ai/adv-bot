from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.product_orders_metrics import ProductOrdersMetrics


T = TypeVar("T", bound="ProductOrdersTextItem")


@_attrs_define
class ProductOrdersTextItem:
    """
    Attributes:
        text (str): Tekst poiskovogo zaprosa
        frequency (int): Kolichestvo obraschenij s poiskovym zaprosom
        date_items (List['ProductOrdersMetrics']): Statistika po datam
    """

    text: str
    frequency: int
    date_items: List["ProductOrdersMetrics"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        text = self.text

        frequency = self.frequency

        date_items = []
        for date_items_item_data in self.date_items:
            date_items_item = date_items_item_data.to_dict()
            date_items.append(date_items_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "text": text,
                "frequency": frequency,
                "dateItems": date_items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.product_orders_metrics import ProductOrdersMetrics

        d = src_dict.copy()
        text = d.pop("text")

        frequency = d.pop("frequency")

        date_items = []
        _date_items = d.pop("dateItems")
        for date_items_item_data in _date_items:
            date_items_item = ProductOrdersMetrics.from_dict(date_items_item_data)

            date_items.append(date_items_item)

        product_orders_text_item = cls(
            text=text,
            frequency=frequency,
            date_items=date_items,
        )

        product_orders_text_item.additional_properties = d
        return product_orders_text_item

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
