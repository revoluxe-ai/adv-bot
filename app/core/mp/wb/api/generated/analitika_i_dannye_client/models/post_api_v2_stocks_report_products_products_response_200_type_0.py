from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_product_response import TableProductResponse


T = TypeVar("T", bound="PostApiV2StocksReportProductsProductsResponse200Type0")


@_attrs_define
class PostApiV2StocksReportProductsProductsResponse200Type0:
    """
    Attributes:
        data (TableProductResponse):
    """

    data: "TableProductResponse"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = self.data.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_product_response import TableProductResponse

        d = src_dict.copy()
        data = TableProductResponse.from_dict(d.pop("data"))

        post_api_v2_stocks_report_products_products_response_200_type_0 = cls(
            data=data,
        )

        post_api_v2_stocks_report_products_products_response_200_type_0.additional_properties = d
        return post_api_v2_stocks_report_products_products_response_200_type_0

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
