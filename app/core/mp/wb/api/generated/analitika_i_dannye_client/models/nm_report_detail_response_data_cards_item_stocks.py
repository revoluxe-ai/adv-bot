from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="NmReportDetailResponseDataCardsItemStocks")


@_attrs_define
class NmReportDetailResponseDataCardsItemStocks:
    """Ostatki

    Attributes:
        stocks_mp (Union[Unset, int]): Ostatki MP, sht. (Obschee kolichestvo ostatkov na skladah prodavtsa na tekuschij
            den')
        stocks_wb (Union[Unset, int]): Ostatki na skladah WB (Obschee kolichestvo ostatkov na skladah WB na tekuschij
            den')
    """

    stocks_mp: Union[Unset, int] = UNSET
    stocks_wb: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        stocks_mp = self.stocks_mp

        stocks_wb = self.stocks_wb

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if stocks_mp is not UNSET:
            field_dict["stocksMp"] = stocks_mp
        if stocks_wb is not UNSET:
            field_dict["stocksWb"] = stocks_wb

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        stocks_mp = d.pop("stocksMp", UNSET)

        stocks_wb = d.pop("stocksWb", UNSET)

        nm_report_detail_response_data_cards_item_stocks = cls(
            stocks_mp=stocks_mp,
            stocks_wb=stocks_wb,
        )

        nm_report_detail_response_data_cards_item_stocks.additional_properties = d
        return nm_report_detail_response_data_cards_item_stocks

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
