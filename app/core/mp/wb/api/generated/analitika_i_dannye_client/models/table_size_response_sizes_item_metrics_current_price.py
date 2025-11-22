from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="TableSizeResponseSizesItemMetricsCurrentPrice")


@_attrs_define
class TableSizeResponseSizesItemMetricsCurrentPrice:
    """Tekuschaja tsena

    Attributes:
        min_price (int): Minimal'naja tsena prodavtsa so skidkoj prodavtsa (bez ucheta skidki WB Kluba) Example: 50.
        max_price (int): Maksimal'naja tsena prodavtsa so skidkoj prodavtsa (bez ucheta skidki WB Kluba) Example: 100.
    """

    min_price: int
    max_price: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        min_price = self.min_price

        max_price = self.max_price

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "minPrice": min_price,
                "maxPrice": max_price,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        min_price = d.pop("minPrice")

        max_price = d.pop("maxPrice")

        table_size_response_sizes_item_metrics_current_price = cls(
            min_price=min_price,
            max_price=max_price,
        )

        table_size_response_sizes_item_metrics_current_price.additional_properties = d
        return table_size_response_sizes_item_metrics_current_price

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
