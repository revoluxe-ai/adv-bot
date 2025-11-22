from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.table_group_item_metrics import TableGroupItemMetrics
    from ..models.table_product_item import TableProductItem


T = TypeVar("T", bound="TableGroupItem")


@_attrs_define
class TableGroupItem:
    """K gruppe tovarov otnosjatsja vse kartochki, podhodjaschie hotja by po odnomu iz parametrov:
    - `subjectName` — nazvanie predmeta
    - `brandName` — brend
    - `tagName` — nazvanie jarlyka

      Attributes:
          metrics (TableGroupItemMetrics): Metriki tovara v tablitse
          items (List['TableProductItem']): Massiv tovarov gruppy
          subject_name (Union[Unset, str]): Nazvanie predmeta Example: Phones.
          subject_id (Union[Unset, int]): ID predmeta Example: 50.
          brand_name (Union[Unset, str]): Brend Example: Apple.
          tag_name (Union[Unset, str]): Nazvanie jarlyka Example: phones.
          tag_id (Union[Unset, int]): ID jarlyka Example: 65.
    """

    metrics: "TableGroupItemMetrics"
    items: List["TableProductItem"]
    subject_name: Union[Unset, str] = UNSET
    subject_id: Union[Unset, int] = UNSET
    brand_name: Union[Unset, str] = UNSET
    tag_name: Union[Unset, str] = UNSET
    tag_id: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        metrics = self.metrics.to_dict()

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        subject_name = self.subject_name

        subject_id = self.subject_id

        brand_name = self.brand_name

        tag_name = self.tag_name

        tag_id = self.tag_id

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "metrics": metrics,
                "items": items,
            }
        )
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if subject_id is not UNSET:
            field_dict["subjectId"] = subject_id
        if brand_name is not UNSET:
            field_dict["brandName"] = brand_name
        if tag_name is not UNSET:
            field_dict["tagName"] = tag_name
        if tag_id is not UNSET:
            field_dict["tagId"] = tag_id

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.table_group_item_metrics import TableGroupItemMetrics
        from ..models.table_product_item import TableProductItem

        d = src_dict.copy()
        metrics = TableGroupItemMetrics.from_dict(d.pop("metrics"))

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = TableProductItem.from_dict(items_item_data)

            items.append(items_item)

        subject_name = d.pop("subjectName", UNSET)

        subject_id = d.pop("subjectId", UNSET)

        brand_name = d.pop("brandName", UNSET)

        tag_name = d.pop("tagName", UNSET)

        tag_id = d.pop("tagId", UNSET)

        table_group_item = cls(
            metrics=metrics,
            items=items,
            subject_name=subject_name,
            subject_id=subject_id,
            brand_name=brand_name,
            tag_name=tag_name,
            tag_id=tag_id,
        )

        table_group_item.additional_properties = d
        return table_group_item

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
