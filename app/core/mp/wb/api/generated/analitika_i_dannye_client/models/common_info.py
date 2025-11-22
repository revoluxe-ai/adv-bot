from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.common_info_advertised_products import CommonInfoAdvertisedProducts
    from ..models.common_info_supplier_rating import CommonInfoSupplierRating


T = TypeVar("T", bound="CommonInfo")


@_attrs_define
class CommonInfo:
    """Obschaja informatsija

    Attributes:
        supplier_rating (CommonInfoSupplierRating): Rejting prodavtsa
        advertised_products (CommonInfoAdvertisedProducts): Kolichestvo tovarov v reklame
        total_products (int): Obschee kolichestvo tovarov Example: 150.
    """

    supplier_rating: "CommonInfoSupplierRating"
    advertised_products: "CommonInfoAdvertisedProducts"
    total_products: int
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        supplier_rating = self.supplier_rating.to_dict()

        advertised_products = self.advertised_products.to_dict()

        total_products = self.total_products

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "supplierRating": supplier_rating,
                "advertisedProducts": advertised_products,
                "totalProducts": total_products,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.common_info_advertised_products import CommonInfoAdvertisedProducts
        from ..models.common_info_supplier_rating import CommonInfoSupplierRating

        d = src_dict.copy()
        supplier_rating = CommonInfoSupplierRating.from_dict(d.pop("supplierRating"))

        advertised_products = CommonInfoAdvertisedProducts.from_dict(d.pop("advertisedProducts"))

        total_products = d.pop("totalProducts")

        common_info = cls(
            supplier_rating=supplier_rating,
            advertised_products=advertised_products,
            total_products=total_products,
        )

        common_info.additional_properties = d
        return common_info

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
