from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_info_advert_params_item_intervals_item import ResponseInfoAdvertParamsItemIntervalsItem
    from ..models.response_info_advert_params_item_nms_item import ResponseInfoAdvertParamsItemNmsItem


T = TypeVar("T", bound="ResponseInfoAdvertParamsItem")


@_attrs_define
class ResponseInfoAdvertParamsItem:
    """
    Attributes:
        subject_name (Union[Unset, str]): Nazvanie predmetnoj gruppy. Dlja kampanij v poiske i rekomendatsijah
            (**ustarevshie tipy kampanij**)
        active (Union[Unset, bool]): Flag aktivnosti predmetnoj gruppy:
              - `true` — aktivna
              - `false` — neaktivna
        intervals (Union[Unset, List['ResponseInfoAdvertParamsItemIntervalsItem']]): Vremennye intervaly pokaza kampanii
        price (Union[Unset, int]): Tekuschaja stavka
        menu_id (Union[Unset, int]): ID menju, gde razmeschaetsja kampanija. Dlja kampanij v kataloge (**ustarevshij tip
            kampanii**)
        subject_id (Union[Unset, int]): ID predmetnoj gruppy, dlja kotoroj sozdana kampanija. Dlja kampanij v poiske i
            rekomendatsijah (**ustarevshie tipy kampanij**
        set_id (Union[Unset, int]): ID sochetanija predmeta i pola. Dlja kampanij v kartochke tovara (**ustarevshij tip
            kampanii**)
        set_name (Union[Unset, str]): Sochetanie predmeta i pola. Dlja kampanij v kartochke tovara (**ustarevshij tip
            kampanii**)
        menu_name (Union[Unset, str]): Nazvanie menju, gde razmeschaetsja kampanija. Dlja kampanij v kataloge
            (**ustarevshij tip kampanii**)
        nms (Union[Unset, List['ResponseInfoAdvertParamsItemNmsItem']]): Massiv kartochek tovarov kampanii
    """

    subject_name: Union[Unset, str] = UNSET
    active: Union[Unset, bool] = UNSET
    intervals: Union[Unset, List["ResponseInfoAdvertParamsItemIntervalsItem"]] = UNSET
    price: Union[Unset, int] = UNSET
    menu_id: Union[Unset, int] = UNSET
    subject_id: Union[Unset, int] = UNSET
    set_id: Union[Unset, int] = UNSET
    set_name: Union[Unset, str] = UNSET
    menu_name: Union[Unset, str] = UNSET
    nms: Union[Unset, List["ResponseInfoAdvertParamsItemNmsItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        subject_name = self.subject_name

        active = self.active

        intervals: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.intervals, Unset):
            intervals = []
            for intervals_item_data in self.intervals:
                intervals_item = intervals_item_data.to_dict()
                intervals.append(intervals_item)

        price = self.price

        menu_id = self.menu_id

        subject_id = self.subject_id

        set_id = self.set_id

        set_name = self.set_name

        menu_name = self.menu_name

        nms: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.nms, Unset):
            nms = []
            for nms_item_data in self.nms:
                nms_item = nms_item_data.to_dict()
                nms.append(nms_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if active is not UNSET:
            field_dict["active"] = active
        if intervals is not UNSET:
            field_dict["intervals"] = intervals
        if price is not UNSET:
            field_dict["price"] = price
        if menu_id is not UNSET:
            field_dict["menuId"] = menu_id
        if subject_id is not UNSET:
            field_dict["subjectId"] = subject_id
        if set_id is not UNSET:
            field_dict["setId"] = set_id
        if set_name is not UNSET:
            field_dict["setName"] = set_name
        if menu_name is not UNSET:
            field_dict["menuName"] = menu_name
        if nms is not UNSET:
            field_dict["nms"] = nms

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.response_info_advert_params_item_intervals_item import ResponseInfoAdvertParamsItemIntervalsItem
        from ..models.response_info_advert_params_item_nms_item import ResponseInfoAdvertParamsItemNmsItem

        d = src_dict.copy()
        subject_name = d.pop("subjectName", UNSET)

        active = d.pop("active", UNSET)

        intervals = []
        _intervals = d.pop("intervals", UNSET)
        for intervals_item_data in _intervals or []:
            intervals_item = ResponseInfoAdvertParamsItemIntervalsItem.from_dict(intervals_item_data)

            intervals.append(intervals_item)

        price = d.pop("price", UNSET)

        menu_id = d.pop("menuId", UNSET)

        subject_id = d.pop("subjectId", UNSET)

        set_id = d.pop("setId", UNSET)

        set_name = d.pop("setName", UNSET)

        menu_name = d.pop("menuName", UNSET)

        nms = []
        _nms = d.pop("nms", UNSET)
        for nms_item_data in _nms or []:
            nms_item = ResponseInfoAdvertParamsItemNmsItem.from_dict(nms_item_data)

            nms.append(nms_item)

        response_info_advert_params_item = cls(
            subject_name=subject_name,
            active=active,
            intervals=intervals,
            price=price,
            menu_id=menu_id,
            subject_id=subject_id,
            set_id=set_id,
            set_name=set_name,
            menu_name=menu_name,
            nms=nms,
        )

        response_info_advert_params_item.additional_properties = d
        return response_info_advert_params_item

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
