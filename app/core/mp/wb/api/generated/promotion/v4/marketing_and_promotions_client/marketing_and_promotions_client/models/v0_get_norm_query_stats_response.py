from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.v0_get_norm_query_stats_item import V0GetNormQueryStatsItem


T = TypeVar("T", bound="V0GetNormQueryStatsResponse")


@_attrs_define
class V0GetNormQueryStatsResponse:
    """Search cluster statistics

    Attributes:
        stats (List['V0GetNormQueryStatsItem']):
    """

    stats: List["V0GetNormQueryStatsItem"]
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        stats = []
        for stats_item_data in self.stats:
            stats_item = stats_item_data.to_dict()
            stats.append(stats_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "stats": stats,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.v0_get_norm_query_stats_item import V0GetNormQueryStatsItem

        d = src_dict.copy()
        stats = []
        _stats = d.pop("stats")
        for stats_item_data in _stats:
            stats_item = V0GetNormQueryStatsItem.from_dict(stats_item_data)

            stats.append(stats_item)

        v0_get_norm_query_stats_response = cls(
            stats=stats,
        )

        v0_get_norm_query_stats_response.additional_properties = d
        return v0_get_norm_query_stats_response

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
