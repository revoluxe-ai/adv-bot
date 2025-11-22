from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.period_orders_request import PeriodOrdersRequest


T = TypeVar("T", bound="ProductOrdersRequest")


@_attrs_define
class ProductOrdersRequest:
    """
    Attributes:
        period (PeriodOrdersRequest): Tekuschij period. Maksimum 7 sutok
        nm_id (int): Artikul WB Example: 211131895.
        search_texts (List[str]): Poiskovye zaprosy. Dlja tarifa
            [Prodvinutyj](https://seller.wildberries.ru/monetization/tariffs) maksimum — 100 Example: ['kostjum',
            'pidzhak'].
    """

    period: "PeriodOrdersRequest"
    nm_id: int
    search_texts: List[str]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        period = self.period.to_dict()

        nm_id = self.nm_id

        search_texts = self.search_texts

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "period": period,
                "nmId": nm_id,
                "searchTexts": search_texts,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.period_orders_request import PeriodOrdersRequest

        d = src_dict.copy()
        period = PeriodOrdersRequest.from_dict(d.pop("period"))

        nm_id = d.pop("nmId")

        search_texts = cast(List[str], d.pop("searchTexts"))

        product_orders_request = cls(
            period=period,
            nm_id=nm_id,
            search_texts=search_texts,
        )

        product_orders_request.additional_properties = d
        return product_orders_request

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
