from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

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
        app_type (int | Unset): Tip platformy:
            - `1` — sajt
            - `32` — Android
            - `64` — IOS
        stats (list[Stats2Item] | Unset):
    """

    app_type: int | Unset = UNSET
    stats: list[Stats2Item] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        app_type = self.app_type

        stats: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.stats, Unset):
            stats = []
            for componentsschemas_stats_2_item_data in self.stats:
                componentsschemas_stats_2_item = (
                    componentsschemas_stats_2_item_data.to_dict()
                )
                stats.append(componentsschemas_stats_2_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if app_type is not UNSET:
            field_dict["app_type"] = app_type
        if stats is not UNSET:
            field_dict["stats"] = stats

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.stats_2_item import Stats2Item

        d = dict(src_dict)
        app_type = d.pop("app_type", UNSET)

        _stats = d.pop("stats", UNSET)
        stats: list[Stats2Item] | Unset = UNSET
        if _stats is not UNSET:
            stats = []
            for componentsschemas_stats_2_item_data in _stats:
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
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
