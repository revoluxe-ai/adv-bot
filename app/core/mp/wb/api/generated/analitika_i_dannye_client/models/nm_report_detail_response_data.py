from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.nm_report_detail_response_data_cards_item import NmReportDetailResponseDataCardsItem


T = TypeVar("T", bound="NmReportDetailResponseData")


@_attrs_define
class NmReportDetailResponseData:
    """
    Attributes:
        page (Union[Unset, int]): Stranitsa Example: 1.
        is_next_page (Union[Unset, bool]): Est' li sledujuschaja stranitsa (`false` — net, `true` — est')
        cards (Union[Unset, List['NmReportDetailResponseDataCardsItem']]):
    """

    page: Union[Unset, int] = UNSET
    is_next_page: Union[Unset, bool] = UNSET
    cards: Union[Unset, List["NmReportDetailResponseDataCardsItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        page = self.page

        is_next_page = self.is_next_page

        cards: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.cards, Unset):
            cards = []
            for cards_item_data in self.cards:
                cards_item = cards_item_data.to_dict()
                cards.append(cards_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if page is not UNSET:
            field_dict["page"] = page
        if is_next_page is not UNSET:
            field_dict["isNextPage"] = is_next_page
        if cards is not UNSET:
            field_dict["cards"] = cards

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.nm_report_detail_response_data_cards_item import NmReportDetailResponseDataCardsItem

        d = src_dict.copy()
        page = d.pop("page", UNSET)

        is_next_page = d.pop("isNextPage", UNSET)

        cards = []
        _cards = d.pop("cards", UNSET)
        for cards_item_data in _cards or []:
            cards_item = NmReportDetailResponseDataCardsItem.from_dict(cards_item_data)

            cards.append(cards_item)

        nm_report_detail_response_data = cls(
            page=page,
            is_next_page=is_next_page,
            cards=cards,
        )

        nm_report_detail_response_data.additional_properties = d
        return nm_report_detail_response_data

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
