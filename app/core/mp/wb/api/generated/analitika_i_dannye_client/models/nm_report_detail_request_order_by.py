from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NmReportDetailRequestOrderBy")


@_attrs_define
class NmReportDetailRequestOrderBy:
    """Parametry sortirovki.
    Esli ne ukazano, to po umolchaniju ispol'zuetsja znachenie "openCard" i sortirovka po ubyvaniju.

    Vse vidy sortirovki `field`:
    - `openCard` — po otkrytiju kartochki (perehod na stranitsu tovara)
    - `addToCart` — po dobavlenijam v korzinu
    - `orders` — po kol-vu zakazov
    - `avgRubPrice` — po srednej tsene v rubljah
    - `ordersSumRub` — po summe zakazov v rubljah
    - `stockMpQty` — po kol-vu ostatkov marketplejsa sht.
    - `stockWbQty` — po kol-vu ostatkov na sklade sht.
    - `cancelSumRub` — summe vozvratov v rubljah
    - `cancelCount` — po kol-vu vozvratov
    - `buyoutCount` — po kol-vu vykupov
    - `buyoutSumRub` — po summe vykupov

        Attributes:
            field (Union[Unset, str]): Vid sortirovki Example: ordersSumRub.
            mode (Union[Unset, str]): `asc` — po vozrastaniju, `desc` — po ubyvaniju
                 Example: asc.
    """

    field: Union[Unset, str] = UNSET
    mode: Union[Unset, str] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        field = self.field

        mode = self.mode

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if field is not UNSET:
            field_dict["field"] = field
        if mode is not UNSET:
            field_dict["mode"] = mode

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        field = d.pop("field", UNSET)

        mode = d.pop("mode", UNSET)

        nm_report_detail_request_order_by = cls(
            field=field,
            mode=mode,
        )

        nm_report_detail_request_order_by.additional_properties = d
        return nm_report_detail_request_order_by

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
