from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.stats_2_item import Stats2Item


T = TypeVar("T", bound="DailyStats2ItemAppTypeStatsItem")


@_attrs_define
class DailyStats2ItemAppTypeStatsItem:
    """
    Attributes:
        app_type (Union[Unset, int]): Platform type:
            - `1` — website
            - `32` — Android
            - `64` — IOS
        stats (Union[Unset, List['Stats2Item']]):
    """

    app_type: Union[Unset, int] = UNSET
    stats: Union[Unset, List["Stats2Item"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        app_type = self.app_type

        stats: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for componentsschemas_stats_2_item_data in self.stats:
                componentsschemas_stats_2_item = (
                    componentsschemas_stats_2_item_data.to_dict()
                )
                stats.append(componentsschemas_stats_2_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if app_type is not UNSET:
            field_dict["app_type"] = app_type
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.stats_2_item import Stats2Item

        d = src_dict.copy()
        app_type = d.pop("app_type", UNSET)

        stats = []
        _stats = d.pop("stats", UNSET)
        for componentsschemas_stats_2_item_data in _stats or []:
            componentsschemas_stats_2_item = Stats2Item.from_dict(
                componentsschemas_stats_2_item_data
            )

            stats.append(componentsschemas_stats_2_item)

        daily_stats_2_item_app_type_stats_item = cls(
            app_type=app_type,
            stats=stats,
        )

        daily_stats_2_item_app_type_stats_item.additional_properties = d
        return daily_stats_2_item_app_type_stats_item

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
