from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.order_by_mode import OrderByMode
from ..models.table_group_field import TableGroupField

T = TypeVar("T", bound="TableOrderBy")


@_attrs_define
class TableOrderBy:
    """Vid sortirovki dannyh

    Attributes:
        field (TableGroupField): Cortirovka po polju:
              - `ordersCount` — Zakazy, sht.
              - `ordersSum` — Zakazy, summa
              - `avgOrders` — Srednee kolichestvo zakazov v den'
              - `buyoutCount` — Vykupy, sht.
              - `buyoutSum` — Vykupy, summa
              - `buyoutPercent` — Protsent vykupa
              - `stockCount` — Ostatki na tekuschij den', sht.
              - `stockSum` — Stoimost' ostatkov na tekuschij den'
              - `saleRate` — Oborachivaemost' tekuschih ostatkov
              - `avgStockTurnover` — Oborachivaemost' srednih ostatkov
              - `toClientCount` — V puti k klientu, sht.
              - `fromClientCount` — V puti ot klienta, sht.
              - `minPrice` — Minimal'naja tsena prodavtsa so skidkoj prodavtsa (bez ucheta skidki WB Kluba)
              - `maxPrice` — Maksimal'naja tsena prodavtsa so skidkoj prodavtsa (bez ucheta skidki WB Kluba)
              - `officeMissingTime` — Vremja otsutstvija tovara na sklade
              - `lostOrdersCount` — Upuschennye zakazy, sht.
              - `lostOrdersSum` — Upuschennye zakazy, summa
              - `lostBuyoutsCount` — Upuschennye vykupy, sht.
              - `lostBuyoutsSum` — Upuschennye vykupy, summa
             Example: avgOrders.
        mode (OrderByMode): Porjadok sortirovki:
            - asc — po vozrastaniju
            - desc — po ubyvaniju
             Example: asc.
    """

    field: TableGroupField
    mode: OrderByMode
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
        field = TableGroupField(d.pop("field"))

        mode = OrderByMode(d.pop("mode"))

        table_order_by = cls(
            field=field,
            mode=mode,
        )

        table_order_by.additional_properties = d
        return table_order_by

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
