from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_grouped_history_response_data_item_history_item import (
        NmReportGroupedHistoryResponseDataItemHistoryItem,
    )
    from ..models.nm_report_grouped_history_response_data_item_object import (
        NmReportGroupedHistoryResponseDataItemObject,
    )
    from ..models.nm_report_grouped_history_response_data_item_tag import NmReportGroupedHistoryResponseDataItemTag


T = TypeVar("T", bound="NmReportGroupedHistoryResponseDataItem")


@_attrs_define
class NmReportGroupedHistoryResponseDataItem:
    """
    Attributes:
        object_ (Union[Unset, NmReportGroupedHistoryResponseDataItemObject]): Predmet
        brand_name (Union[Unset, str]): Brend Example: Some.
        tag (Union[Unset, NmReportGroupedHistoryResponseDataItemTag]): Jarlyk
        history (Union[Unset, List['NmReportGroupedHistoryResponseDataItemHistoryItem']]):
    """

    object_: Union[Unset, "NmReportGroupedHistoryResponseDataItemObject"] = UNSET
    brand_name: Union[Unset, str] = UNSET
    tag: Union[Unset, "NmReportGroupedHistoryResponseDataItemTag"] = UNSET
    history: Union[Unset, List["NmReportGroupedHistoryResponseDataItemHistoryItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        object_: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.object_, Unset):
            object_ = self.object_.to_dict()

        brand_name = self.brand_name

        tag: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.tag, Unset):
            tag = self.tag.to_dict()

        history: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.history, Unset):
            history = []
            for history_item_data in self.history:
                history_item = history_item_data.to_dict()
                history.append(history_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if object_ is not UNSET:
            field_dict["object"] = object_
        if brand_name is not UNSET:
            field_dict["brandName"] = brand_name
        if tag is not UNSET:
            field_dict["tag"] = tag
        if history is not UNSET:
            field_dict["history"] = history

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_grouped_history_response_data_item_history_item import (
            NmReportGroupedHistoryResponseDataItemHistoryItem,
        )
        from ..models.nm_report_grouped_history_response_data_item_object import (
            NmReportGroupedHistoryResponseDataItemObject,
        )
        from ..models.nm_report_grouped_history_response_data_item_tag import NmReportGroupedHistoryResponseDataItemTag

        d = src_dict.copy()
        _object_ = d.pop("object", UNSET)
        object_: Union[Unset, NmReportGroupedHistoryResponseDataItemObject]
        if isinstance(_object_, Unset):
            object_ = UNSET
        else:
            object_ = NmReportGroupedHistoryResponseDataItemObject.from_dict(_object_)

        brand_name = d.pop("brandName", UNSET)

        _tag = d.pop("tag", UNSET)
        tag: Union[Unset, NmReportGroupedHistoryResponseDataItemTag]
        if isinstance(_tag, Unset):
            tag = UNSET
        else:
            tag = NmReportGroupedHistoryResponseDataItemTag.from_dict(_tag)

        history = []
        _history = d.pop("history", UNSET)
        for history_item_data in _history or []:
            history_item = NmReportGroupedHistoryResponseDataItemHistoryItem.from_dict(history_item_data)

            history.append(history_item)

        nm_report_grouped_history_response_data_item = cls(
            object_=object_,
            brand_name=brand_name,
            tag=tag,
            history=history,
        )

        nm_report_grouped_history_response_data_item.additional_properties = d
        return nm_report_grouped_history_response_data_item

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
