from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.position_info_average import PositionInfoAverage
    from ..models.position_info_median import PositionInfoMedian
    from ..models.search_report_position_chart_item import SearchReportPositionChartItem
    from ..models.search_report_position_clusters import SearchReportPositionClusters


T = TypeVar("T", bound="PositionInfo")


@_attrs_define
class PositionInfo:
    """Informatsija o pozitsii tovara

    Attributes:
        average (PositionInfoAverage): Srednjaja pozitsija tovara v rezul'tatah poiska
        median (PositionInfoMedian): Mediannaja pozitsija tovara v rezul'tatah poiska
        chart_items (List['SearchReportPositionChartItem']): Dannye dlja charta po srednej i mediannoj pozitsii tovara v
            rezul'tatah poiska
        clusters (SearchReportPositionClusters): Kolichestvo tovarov so srednej pozitsiej v poiske:
              - `firstHundred` — ot 1 do 100
              - `secondHundred` — ot 101 do 200
              - `below` — ot 201 i nizhe
    """

    average: "PositionInfoAverage"
    median: "PositionInfoMedian"
    chart_items: List["SearchReportPositionChartItem"]
    clusters: "SearchReportPositionClusters"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        average = self.average.to_dict()

        median = self.median.to_dict()

        chart_items = []
        for chart_items_item_data in self.chart_items:
            chart_items_item = chart_items_item_data.to_dict()
            chart_items.append(chart_items_item)

        clusters = self.clusters.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "average": average,
                "median": median,
                "chartItems": chart_items,
                "clusters": clusters,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.position_info_average import PositionInfoAverage
        from ..models.position_info_median import PositionInfoMedian
        from ..models.search_report_position_chart_item import SearchReportPositionChartItem
        from ..models.search_report_position_clusters import SearchReportPositionClusters

        d = src_dict.copy()
        average = PositionInfoAverage.from_dict(d.pop("average"))

        median = PositionInfoMedian.from_dict(d.pop("median"))

        chart_items = []
        _chart_items = d.pop("chartItems")
        for chart_items_item_data in _chart_items:
            chart_items_item = SearchReportPositionChartItem.from_dict(chart_items_item_data)

            chart_items.append(chart_items_item)

        clusters = SearchReportPositionClusters.from_dict(d.pop("clusters"))

        position_info = cls(
            average=average,
            median=median,
            chart_items=chart_items,
            clusters=clusters,
        )

        position_info.additional_properties = d
        return position_info

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
