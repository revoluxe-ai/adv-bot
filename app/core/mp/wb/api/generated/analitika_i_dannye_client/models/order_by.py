from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.order_by_field import OrderByField
from ..models.order_by_mode import OrderByMode

T = TypeVar("T", bound="OrderBy")


@_attrs_define
class OrderBy:
    """Parametry sortirovki

    Attributes:
        field (OrderByField): Pole dlja sortirovki:
              - `openCard` — Pereshli v kartochku
              - `addToCart` — Polozhili v korzinu
              - `orderCount` — Zakazali tovarov, sht
              - `orderSum` — Zakazali na summu
              - `buyoutCount` — Vykupili tovarov, sht
              - `buyoutSum` — Vykupili na summu
              - `cancelCount` — Otmenili tovarov, sht
              - `cancelSum` — Otmenili na summu
              - `avgPrice` — Srednjaja tsena
              - `stockMpQty` — Ostatki na skladah prodavtsa, sht
              - `stockWbQty` — Ostatki na skladah WB, sht
              - `shareOrderPercent` — Dolja v vyruchke
              - `addToWishlist` — Dobavili v **Otlozhennye**
              - `timeToReady` — Crednee vremja dostavki
              - `localizationPercent` — Lokal'nye zakazy v ramkah odnogo regiona
              - `wbClub.orderCount` — Zakazali tovarov s WB Klubom, sht
              - `wbClub.orderSum` — Zakazali na summu s WB Klubom
              - `wbClub.buyoutSum` — Vykupili tovarov s WB Klubom, sht
              - `wbClub.buyoutCount` — Protsent vykupa s WB Klubom
              - `wbClub.cancelSum` — Otmenili tovarov s WB Klubom, sht
              - `wbClub.avgPrice` — Srednjaja tsena s WB Klubom
              - `wbClub.buyoutPercent` — Protsent vykupa s WB Klubom
              - `wbClub.avgOrderCountPerDay` — Srednee kolichestvo zakazov v den' s WB Klubom, sht
              - `wbClub.cancelCount` — Otmenili tovarov s WB Klubom, sht
             Default: OrderByField.OPENCARD. Example: openCard.
        mode (OrderByMode): Porjadok sortirovki:
              - `asc` — po vozrastaniju
              - `desc` — po ubyvaniju
             Default: OrderByMode.DESC.
    """

    field: OrderByField = OrderByField.OPENCARD
    mode: OrderByMode = OrderByMode.DESC
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
        field = OrderByField(d.pop("field"))

        mode = OrderByMode(d.pop("mode"))

        order_by = cls(
            field=field,
            mode=mode,
        )

        order_by.additional_properties = d
        return order_by

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
