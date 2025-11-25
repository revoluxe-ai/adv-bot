from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_product_item_st_metrics import TableProductItemStMetrics


T = TypeVar("T", bound="TableProductItemSt")


@_attrs_define
class TableProductItemSt:
    """Dannye po tovaru

    Attributes:
        nm_id (int): Artikul WB Example: 123456789.
        is_deleted (bool): Javljaetsja li tovar udalennym
        subject_name (str): Nazvanie predmeta Example: Printery.
        name (str): Nazvanie tovara Example: Pechatnik 3000.
        vendor_code (str): Artikul prodavtsa Example: pechatnik3000.
        brand_name (str): Brend Example: Kompik.
        main_photo (str): Ssylka na glavnoe foto Example:
            https://basket-12.wbbasket.ru/vol1788/part178840/178840836/images/c246x328/1.webp.
        has_sizes (bool): Javljaetsja li tovar razmernym. Nerazmernyj tovar imeet edinstvennyj razmer, s
            `"techSize":"0"` Example: True.
        metrics (TableProductItemStMetrics): Metriki tovara
    """

    nm_id: int
    is_deleted: bool
    subject_name: str
    name: str
    vendor_code: str
    brand_name: str
    main_photo: str
    has_sizes: bool
    metrics: "TableProductItemStMetrics"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        is_deleted = self.is_deleted

        subject_name = self.subject_name

        name = self.name

        vendor_code = self.vendor_code

        brand_name = self.brand_name

        main_photo = self.main_photo

        has_sizes = self.has_sizes

        metrics = self.metrics.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmID": nm_id,
                "isDeleted": is_deleted,
                "subjectName": subject_name,
                "name": name,
                "vendorCode": vendor_code,
                "brandName": brand_name,
                "mainPhoto": main_photo,
                "hasSizes": has_sizes,
                "metrics": metrics,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_product_item_st_metrics import TableProductItemStMetrics

        d = src_dict.copy()
        nm_id = d.pop("nmID")

        is_deleted = d.pop("isDeleted")

        subject_name = d.pop("subjectName")

        name = d.pop("name")

        vendor_code = d.pop("vendorCode")

        brand_name = d.pop("brandName")

        main_photo = d.pop("mainPhoto")

        has_sizes = d.pop("hasSizes")

        metrics = TableProductItemStMetrics.from_dict(d.pop("metrics"))

        table_product_item_st = cls(
            nm_id=nm_id,
            is_deleted=is_deleted,
            subject_name=subject_name,
            name=name,
            vendor_code=vendor_code,
            brand_name=brand_name,
            main_photo=main_photo,
            has_sizes=has_sizes,
            metrics=metrics,
        )

        table_product_item_st.additional_properties = d
        return table_product_item_st

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
