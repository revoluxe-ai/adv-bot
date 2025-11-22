from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.grouped_history_response_item import GroupedHistoryResponseItem


T = TypeVar("T", bound="PostSalesFunnelGroupedHistoryResponse200")


@_attrs_define
class PostSalesFunnelGroupedHistoryResponse200:
    """
    Attributes:
        data (List['GroupedHistoryResponseItem']): Statistika
    """

    data: List["GroupedHistoryResponseItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = []
        for componentsschemas_grouped_history_response_item_data in self.data:
            componentsschemas_grouped_history_response_item = (
                componentsschemas_grouped_history_response_item_data.to_dict()
            )
            data.append(componentsschemas_grouped_history_response_item)

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
        from ..models.grouped_history_response_item import GroupedHistoryResponseItem

        d = src_dict.copy()
        data = []
        _data = d.pop("data")
        for componentsschemas_grouped_history_response_item_data in _data:
            componentsschemas_grouped_history_response_item = GroupedHistoryResponseItem.from_dict(
                componentsschemas_grouped_history_response_item_data
            )

            data.append(componentsschemas_grouped_history_response_item)

        post_sales_funnel_grouped_history_response_200 = cls(
            data=data,
        )

        post_sales_funnel_grouped_history_response_200.additional_properties = d
        return post_sales_funnel_grouped_history_response_200

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
