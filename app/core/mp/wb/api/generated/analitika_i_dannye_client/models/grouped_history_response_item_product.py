from typing import Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="GroupedHistoryResponseItemProduct")


@_attrs_define
class GroupedHistoryResponseItemProduct:
    """
    Attributes:
        nm_id (int): Artikul WB Example: 268913787.
        title (str): Nazvanie kartochki tovara Example: Krossovki dlja bega.
        vendor_code (str): Artikul prodavtsa Example: 12345456.
        brand_name (str): Brend Example: Demix.
        subject_id (int): ID predmeta Example: 105.
        subject_name (str): Nazvanie predmeta Example: Krossovki.
    """

    nm_id: int
    title: str
    vendor_code: str
    brand_name: str
    subject_id: int
    subject_name: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        title = self.title

        vendor_code = self.vendor_code

        brand_name = self.brand_name

        subject_id = self.subject_id

        subject_name = self.subject_name

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmId": nm_id,
                "title": title,
                "vendorCode": vendor_code,
                "brandName": brand_name,
                "subjectId": subject_id,
                "subjectName": subject_name,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        nm_id = d.pop("nmId")

        title = d.pop("title")

        vendor_code = d.pop("vendorCode")

        brand_name = d.pop("brandName")

        subject_id = d.pop("subjectId")

        subject_name = d.pop("subjectName")

        grouped_history_response_item_product = cls(
            nm_id=nm_id,
            title=title,
            vendor_code=vendor_code,
            brand_name=brand_name,
            subject_id=subject_id,
            subject_name=subject_name,
        )

        grouped_history_response_item_product.additional_properties = d
        return grouped_history_response_item_product

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
