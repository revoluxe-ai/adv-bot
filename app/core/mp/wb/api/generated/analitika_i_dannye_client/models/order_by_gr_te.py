from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.order_by_gr_te_field import OrderByGrTeField
from ..models.order_by_gr_te_mode import OrderByGrTeMode

T = TypeVar("T", bound="OrderByGrTe")


@_attrs_define
class OrderByGrTe:
    """Parametry sortirovki

    Attributes:
        field (OrderByGrTeField): Pole dlja sortirovki:
              - `avgPosition` — po srednej pozitsii
              - `addToCart` — po dobavlenijam v korzinu
              - `openCard` — po otkrytiju kartochki (perehod na stranitsu tovara)
              - `orders` — po kolichestvu zakazov
              - `cartToOrder` — po konversii v zakaz iz poiska
              - `openToCart` — po konversii v korzinu iz poiska
              - `visibility` — po vidimosti tovara
             Example: avgPosition.
        mode (OrderByGrTeMode): Porjadok sortirovki:
              - `asc` — po vozrastaniju
              - `desc` — po ubyvaniju
             Example: asc.
    """

    field: OrderByGrTeField
    mode: OrderByGrTeMode
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        field = self.field.value

        mode = self.mode.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "field": field,
                "mode": mode,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        field = OrderByGrTeField(d.pop("field"))

        mode = OrderByGrTeMode(d.pop("mode"))

        order_by_gr_te = cls(
            field=field,
            mode=mode,
        )

        order_by_gr_te.additional_properties = d
        return order_by_gr_te

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
