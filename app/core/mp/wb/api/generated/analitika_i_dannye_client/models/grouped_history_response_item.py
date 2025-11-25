from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.grouped_history_response_item_product import GroupedHistoryResponseItemProduct
    from ..models.history import History


T = TypeVar("T", bound="GroupedHistoryResponseItem")


@_attrs_define
class GroupedHistoryResponseItem:
    """
    Attributes:
        product (GroupedHistoryResponseItemProduct):
        history (List['History']): Statistika za period
    """

    product: "GroupedHistoryResponseItemProduct"
    history: List["History"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        product = self.product.to_dict()

        history = []
        for history_item_data in self.history:
            history_item = history_item_data.to_dict()
            history.append(history_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "product": product,
                "history": history,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.grouped_history_response_item_product import GroupedHistoryResponseItemProduct
        from ..models.history import History

        d = src_dict.copy()
        product = GroupedHistoryResponseItemProduct.from_dict(d.pop("product"))

        history = []
        _history = d.pop("history")
        for history_item_data in _history:
            history_item = History.from_dict(history_item_data)

            history.append(history_item)

        grouped_history_response_item = cls(
            product=product,
            history=history,
        )

        grouped_history_response_item.additional_properties = d
        return grouped_history_response_item

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
