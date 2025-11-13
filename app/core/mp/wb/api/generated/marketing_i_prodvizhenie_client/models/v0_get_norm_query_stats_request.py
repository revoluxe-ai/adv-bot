import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_stats_request_items_item import V0GetNormQueryStatsRequestItemsItem


T = TypeVar("T", bound="V0GetNormQueryStatsRequest")


@_attrs_define
class V0GetNormQueryStatsRequest:
    """
    Attributes:
        from_ (datetime.date): Data nachala perioda Example: 2025-10-07.
        to (datetime.date): Data okonchanija perioda Example: 2025-10-08.
        items (List['V0GetNormQueryStatsRequestItemsItem']):
    """

    from_: datetime.date
    to: datetime.date
    items: List["V0GetNormQueryStatsRequestItemsItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        from_ = self.from_.isoformat()

        to = self.to.isoformat()

        items = []
        for items_item_data in self.items:
            items_item = items_item_data.to_dict()
            items.append(items_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "from": from_,
                "to": to,
                "items": items,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_get_norm_query_stats_request_items_item import V0GetNormQueryStatsRequestItemsItem

        d = src_dict.copy()
        from_ = isoparse(d.pop("from")).date()

        to = isoparse(d.pop("to")).date()

        items = []
        _items = d.pop("items")
        for items_item_data in _items:
            items_item = V0GetNormQueryStatsRequestItemsItem.from_dict(items_item_data)

            items.append(items_item)

        v0_get_norm_query_stats_request = cls(
            from_=from_,
            to=to,
            items=items,
        )

        v0_get_norm_query_stats_request.additional_properties = d
        return v0_get_norm_query_stats_request

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
