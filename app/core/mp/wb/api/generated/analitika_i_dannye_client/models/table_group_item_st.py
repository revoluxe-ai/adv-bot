from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.table_common_metrics import TableCommonMetrics
    from ..models.table_product_item_st import TableProductItemSt


T = TypeVar("T", bound="TableGroupItemSt")


@_attrs_define
class TableGroupItemSt:
    """Dannye po gruppe

    Attributes:
        subject_id (int): ID predmeta Example: 123456789.
        subject_name (str): Nazvanie predmeta Example: Kruzhka.
        brand_name (str): Brend Example: Krutaja posuda.
        tag_id (int): ID jarlyka Example: 12345.
        tag_name (str): Nazvanie jarlyka Example: Chelovek-Pauk.
        metrics (TableCommonMetrics): Metriki
        items (List['TableProductItemSt']): Tovary gruppy
    """

    subject_id: int
    subject_name: str
    brand_name: str
    tag_id: int
    tag_name: str
    metrics: "TableCommonMetrics"
    items: List["TableProductItemSt"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        subject_id = self.subject_id

        subject_name = self.subject_name

        brand_name = self.brand_name

        tag_id = self.tag_id

        tag_name = self.tag_name

        metrics = self.metrics.to_dict()

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "subjectID": subject_id,
                "subjectName": subject_name,
                "brandName": brand_name,
                "tagID": tag_id,
                "tagName": tag_name,
                "metrics": metrics,
                "items": items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_common_metrics import TableCommonMetrics
        from ..models.table_product_item_st import TableProductItemSt

        d = src_dict.copy()
        subject_id = d.pop("subjectID")

        subject_name = d.pop("subjectName")

        brand_name = d.pop("brandName")

        tag_id = d.pop("tagID")

        tag_name = d.pop("tagName")

        metrics = TableCommonMetrics.from_dict(d.pop("metrics"))

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = TableProductItemSt.from_dict(items_item_data)

            items.append(items_item)

        table_group_item_st = cls(
            subject_id=subject_id,
            subject_name=subject_name,
            brand_name=brand_name,
            tag_id=tag_id,
            tag_name=tag_name,
            metrics=metrics,
            items=items,
        )

        table_group_item_st.additional_properties = d
        return table_group_item_st

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
