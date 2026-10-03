from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetApiV1AnalyticsBannedProductsShadowedResponse200ReportItem")


@_attrs_define
class GetApiV1AnalyticsBannedProductsShadowedResponse200ReportItem:
    """
    Attributes:
        brand (Union[Unset, str]): Brand Example: Трикотаж.
        nm_id (Union[Unset, int]): WB item number Example: 166658151.
        title (Union[Unset, str]): Item title Example: ВАЗ.
        vendor_code (Union[Unset, str]): Seller item number Example: DP02/черный.
        nm_rating (Union[Unset, float]): Listing rating Example: 3.1.
    """

    brand: Union[Unset, str] = UNSET
    nm_id: Union[Unset, int] = UNSET
    title: Union[Unset, str] = UNSET
    vendor_code: Union[Unset, str] = UNSET
    nm_rating: Union[Unset, float] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        brand = self.brand

        nm_id = self.nm_id

        title = self.title

        vendor_code = self.vendor_code

        nm_rating = self.nm_rating

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if brand is not UNSET:
            field_dict["brand"] = brand
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if title is not UNSET:
            field_dict["title"] = title
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if nm_rating is not UNSET:
            field_dict["nmRating"] = nm_rating

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        brand = d.pop("brand", UNSET)

        nm_id = d.pop("nmId", UNSET)

        title = d.pop("title", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        nm_rating = d.pop("nmRating", UNSET)

        get_api_v1_analytics_banned_products_shadowed_response_200_report_item = cls(
            brand=brand,
            nm_id=nm_id,
            title=title,
            vendor_code=vendor_code,
            nm_rating=nm_rating,
        )

        get_api_v1_analytics_banned_products_shadowed_response_200_report_item.additional_properties = d
        return get_api_v1_analytics_banned_products_shadowed_response_200_report_item

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
