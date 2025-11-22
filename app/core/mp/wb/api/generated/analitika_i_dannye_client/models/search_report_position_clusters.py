from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.search_report_position_clusters_below import SearchReportPositionClustersBelow
    from ..models.search_report_position_clusters_first_hundred import SearchReportPositionClustersFirstHundred
    from ..models.search_report_position_clusters_second_hundred import SearchReportPositionClustersSecondHundred


T = TypeVar("T", bound="SearchReportPositionClusters")


@_attrs_define
class SearchReportPositionClusters:
    """Kolichestvo tovarov so srednej pozitsiej v poiske:
    - `firstHundred` — ot 1 do 100
    - `secondHundred` — ot 101 do 200
    - `below` — ot 201 i nizhe

      Attributes:
          first_hundred (SearchReportPositionClustersFirstHundred): ot 1 do 100
          second_hundred (SearchReportPositionClustersSecondHundred): ot 101 do 200
          below (SearchReportPositionClustersBelow): ot 201 i nizhe
    """

    first_hundred: "SearchReportPositionClustersFirstHundred"
    second_hundred: "SearchReportPositionClustersSecondHundred"
    below: "SearchReportPositionClustersBelow"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        first_hundred = self.first_hundred.to_dict()

        second_hundred = self.second_hundred.to_dict()

        below = self.below.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "firstHundred": first_hundred,
                "secondHundred": second_hundred,
                "below": below,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.search_report_position_clusters_below import SearchReportPositionClustersBelow
        from ..models.search_report_position_clusters_first_hundred import SearchReportPositionClustersFirstHundred
        from ..models.search_report_position_clusters_second_hundred import SearchReportPositionClustersSecondHundred

        d = src_dict.copy()
        first_hundred = SearchReportPositionClustersFirstHundred.from_dict(d.pop("firstHundred"))

        second_hundred = SearchReportPositionClustersSecondHundred.from_dict(d.pop("secondHundred"))

        below = SearchReportPositionClustersBelow.from_dict(d.pop("below"))

        search_report_position_clusters = cls(
            first_hundred=first_hundred,
            second_hundred=second_hundred,
            below=below,
        )

        search_report_position_clusters.additional_properties = d
        return search_report_position_clusters

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
