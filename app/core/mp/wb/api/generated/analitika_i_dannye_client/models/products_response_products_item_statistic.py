from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.statistics_comparison import StatisticsComparison
    from ..models.statistics_past import StatisticsPast
    from ..models.statistics_selected import StatisticsSelected


T = TypeVar("T", bound="ProductsResponseProductsItemStatistic")


@_attrs_define
class ProductsResponseProductsItemStatistic:
    """
    Attributes:
        selected (StatisticsSelected):
        past (Union[Unset, StatisticsPast]):
        comparison (Union[Unset, StatisticsComparison]):
    """

    selected: "StatisticsSelected"
    past: Union[Unset, "StatisticsPast"] = UNSET
    comparison: Union[Unset, "StatisticsComparison"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        selected = self.selected.to_dict()

        past: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.past, Unset):
            past = self.past.to_dict()

        comparison: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.comparison, Unset):
            comparison = self.comparison.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "selected": selected,
            }
        )
        if past is not UNSET:
            field_dict["past"] = past
        if comparison is not UNSET:
            field_dict["comparison"] = comparison

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.statistics_comparison import StatisticsComparison
        from ..models.statistics_past import StatisticsPast
        from ..models.statistics_selected import StatisticsSelected

        d = src_dict.copy()
        selected = StatisticsSelected.from_dict(d.pop("selected"))

        _past = d.pop("past", UNSET)
        past: Union[Unset, StatisticsPast]
        if isinstance(_past, Unset):
            past = UNSET
        else:
            past = StatisticsPast.from_dict(_past)

        _comparison = d.pop("comparison", UNSET)
        comparison: Union[Unset, StatisticsComparison]
        if isinstance(_comparison, Unset):
            comparison = UNSET
        else:
            comparison = StatisticsComparison.from_dict(_comparison)

        products_response_products_item_statistic = cls(
            selected=selected,
            past=past,
            comparison=comparison,
        )

        products_response_products_item_statistic.additional_properties = d
        return products_response_products_item_statistic

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
