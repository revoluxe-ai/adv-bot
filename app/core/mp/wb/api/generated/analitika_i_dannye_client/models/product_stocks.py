from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ProductStocks")


@_attrs_define
class ProductStocks:
    """Ostatki

    Attributes:
        wb (int): Obschee kolichestvo ostatkov na skladah WB na tekuschij den', sht.
        mp (int): Obschee kolichestvo ostatkov na skladah prodavtsa na tekuschij den', sht.
        balance_sum (int): Summa ostatkov na skladah
    """

    wb: int
    mp: int
    balance_sum: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        wb = self.wb

        mp = self.mp

        balance_sum = self.balance_sum

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "wb": wb,
                "mp": mp,
                "balanceSum": balance_sum,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        wb = d.pop("wb")

        mp = d.pop("mp")

        balance_sum = d.pop("balanceSum")

        product_stocks = cls(
            wb=wb,
            mp=mp,
            balance_sum=balance_sum,
        )

        product_stocks.additional_properties = d
        return product_stocks

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
