from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.products_response_products_item_product import ProductsResponseProductsItemProduct
    from ..models.products_response_products_item_statistic import ProductsResponseProductsItemStatistic


T = TypeVar("T", bound="ProductsResponseProductsItem")


@_attrs_define
class ProductsResponseProductsItem:
    """
    Attributes:
        product (ProductsResponseProductsItemProduct):
        statistic (ProductsResponseProductsItemStatistic):
    """

    product: "ProductsResponseProductsItemProduct"
    statistic: "ProductsResponseProductsItemStatistic"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        product = self.product.to_dict()

        statistic = self.statistic.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "product": product,
                "statistic": statistic,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.products_response_products_item_product import ProductsResponseProductsItemProduct
        from ..models.products_response_products_item_statistic import ProductsResponseProductsItemStatistic

        d = src_dict.copy()
        product = ProductsResponseProductsItemProduct.from_dict(d.pop("product"))

        statistic = ProductsResponseProductsItemStatistic.from_dict(d.pop("statistic"))

        products_response_products_item = cls(
            product=product,
            statistic=statistic,
        )

        products_response_products_item.additional_properties = d
        return products_response_products_item

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
