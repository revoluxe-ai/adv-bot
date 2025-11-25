from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_product_item import TableProductItem


T = TypeVar("T", bound="TableDetailsResponse")


@_attrs_define
class TableDetailsResponse:
    """
    Attributes:
        products (List['TableProductItem']): Spisok tovarov v gruppe po fil'tru
    """

    products: List["TableProductItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        products = []
        for products_item_data in self.products:
            products_item = products_item_data.to_dict()
            products.append(products_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "products": products,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_product_item import TableProductItem

        d = src_dict.copy()
        products = []
        _products = d.pop("products")
        for products_item_data in _products:
            products_item = TableProductItem.from_dict(products_item_data)

            products.append(products_item)

        table_details_response = cls(
            products=products,
        )

        table_details_response.additional_properties = d
        return table_details_response

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
