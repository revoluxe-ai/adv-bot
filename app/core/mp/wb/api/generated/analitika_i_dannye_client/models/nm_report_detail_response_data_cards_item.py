from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_response_data_cards_item_object import NmReportDetailResponseDataCardsItemObject
    from ..models.nm_report_detail_response_data_cards_item_statistics import (
        NmReportDetailResponseDataCardsItemStatistics,
    )
    from ..models.nm_report_detail_response_data_cards_item_stocks import NmReportDetailResponseDataCardsItemStocks
    from ..models.nm_report_detail_response_data_cards_item_tags_item import NmReportDetailResponseDataCardsItemTagsItem


T = TypeVar("T", bound="NmReportDetailResponseDataCardsItem")


@_attrs_define
class NmReportDetailResponseDataCardsItem:
    """
    Attributes:
        nm_id (Union[Unset, int]): Artikul WB Example: 1234567.
        vendor_code (Union[Unset, str]): Artikul prodavtsa Example: supplierVendor.
        brand_name (Union[Unset, str]): Brend Example: Some.
        tags (Union[Unset, List['NmReportDetailResponseDataCardsItemTagsItem']]): Jarlyki
        object_ (Union[Unset, NmReportDetailResponseDataCardsItemObject]): Predmet
        statistics (Union[Unset, NmReportDetailResponseDataCardsItemStatistics]): Statistika
        stocks (Union[Unset, NmReportDetailResponseDataCardsItemStocks]): Ostatki
    """

    nm_id: Union[Unset, int] = UNSET
    vendor_code: Union[Unset, str] = UNSET
    brand_name: Union[Unset, str] = UNSET
    tags: Union[Unset, List["NmReportDetailResponseDataCardsItemTagsItem"]] = UNSET
    object_: Union[Unset, "NmReportDetailResponseDataCardsItemObject"] = UNSET
    statistics: Union[Unset, "NmReportDetailResponseDataCardsItemStatistics"] = UNSET
    stocks: Union[Unset, "NmReportDetailResponseDataCardsItemStocks"] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm_id = self.nm_id

        vendor_code = self.vendor_code

        brand_name = self.brand_name

        tags: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.tags, Unset):
            tags = []
            for tags_item_data in self.tags:
                tags_item = tags_item_data.to_dict()
                tags.append(tags_item)

        object_: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.object_, Unset):
            object_ = self.object_.to_dict()

        statistics: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.statistics, Unset):
            statistics = self.statistics.to_dict()

        stocks: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.stocks, Unset):
            stocks = self.stocks.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if brand_name is not UNSET:
            field_dict["brandName"] = brand_name
        if tags is not UNSET:
            field_dict["tags"] = tags
        if object_ is not UNSET:
            field_dict["object"] = object_
        if statistics is not UNSET:
            field_dict["statistics"] = statistics
        if stocks is not UNSET:
            field_dict["stocks"] = stocks

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_response_data_cards_item_object import NmReportDetailResponseDataCardsItemObject
        from ..models.nm_report_detail_response_data_cards_item_statistics import (
            NmReportDetailResponseDataCardsItemStatistics,
        )
        from ..models.nm_report_detail_response_data_cards_item_stocks import NmReportDetailResponseDataCardsItemStocks
        from ..models.nm_report_detail_response_data_cards_item_tags_item import (
            NmReportDetailResponseDataCardsItemTagsItem,
        )

        d = src_dict.copy()
        nm_id = d.pop("nmID", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        brand_name = d.pop("brandName", UNSET)

        tags = []
        _tags = d.pop("tags", UNSET)
        for tags_item_data in _tags or []:
            tags_item = NmReportDetailResponseDataCardsItemTagsItem.from_dict(tags_item_data)

            tags.append(tags_item)

        _object_ = d.pop("object", UNSET)
        object_: Union[Unset, NmReportDetailResponseDataCardsItemObject]
        if isinstance(_object_, Unset):
            object_ = UNSET
        else:
            object_ = NmReportDetailResponseDataCardsItemObject.from_dict(_object_)

        _statistics = d.pop("statistics", UNSET)
        statistics: Union[Unset, NmReportDetailResponseDataCardsItemStatistics]
        if isinstance(_statistics, Unset):
            statistics = UNSET
        else:
            statistics = NmReportDetailResponseDataCardsItemStatistics.from_dict(_statistics)

        _stocks = d.pop("stocks", UNSET)
        stocks: Union[Unset, NmReportDetailResponseDataCardsItemStocks]
        if isinstance(_stocks, Unset):
            stocks = UNSET
        else:
            stocks = NmReportDetailResponseDataCardsItemStocks.from_dict(_stocks)

        nm_report_detail_response_data_cards_item = cls(
            nm_id=nm_id,
            vendor_code=vendor_code,
            brand_name=brand_name,
            tags=tags,
            object_=object_,
            statistics=statistics,
            stocks=stocks,
        )

        nm_report_detail_response_data_cards_item.additional_properties = d
        return nm_report_detail_response_data_cards_item

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
