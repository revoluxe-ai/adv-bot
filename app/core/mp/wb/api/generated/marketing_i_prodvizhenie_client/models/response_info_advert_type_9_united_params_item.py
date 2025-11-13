from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_info_advert_type_9_united_params_item_menus_item import (
        ResponseInfoAdvertType9UnitedParamsItemMenusItem,
    )
    from ..models.response_info_advert_type_9_united_params_item_subject import (
        ResponseInfoAdvertType9UnitedParamsItemSubject,
    )


T = TypeVar("T", bound="ResponseInfoAdvertType9UnitedParamsItem")


@_attrs_define
class ResponseInfoAdvertType9UnitedParamsItem:
    """
    Attributes:
        subject (Union[Unset, ResponseInfoAdvertType9UnitedParamsItemSubject]): Prodvigaemyj predmet
        menus (Union[Unset, List['ResponseInfoAdvertType9UnitedParamsItemMenusItem']]):
        nms (Union[Unset, List[int]]): Artikuly WB
        search_cpm (Union[Unset, int]): Stavka v poiske
        catalog_cpm (Union[Unset, int]): Stavka v Kataloge
    """

    subject: Union[Unset, "ResponseInfoAdvertType9UnitedParamsItemSubject"] = UNSET
    menus: Union[Unset, List["ResponseInfoAdvertType9UnitedParamsItemMenusItem"]] = UNSET
    nms: Union[Unset, List[int]] = UNSET
    search_cpm: Union[Unset, int] = UNSET
    catalog_cpm: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        subject: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.subject, Unset):
            subject = self.subject.to_dict()

        menus: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.menus, Unset):
            menus = []
            for menus_item_data in self.menus:
                menus_item = menus_item_data.to_dict()
                menus.append(menus_item)

        nms: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        search_cpm = self.search_cpm

        catalog_cpm = self.catalog_cpm

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if subject is not UNSET:
            field_dict["subject"] = subject
        if menus is not UNSET:
            field_dict["menus"] = menus
        if nms is not UNSET:
            field_dict["nms"] = nms
        if search_cpm is not UNSET:
            field_dict["searchCPM"] = search_cpm
        if catalog_cpm is not UNSET:
            field_dict["catalogCPM"] = catalog_cpm

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.response_info_advert_type_9_united_params_item_menus_item import (
            ResponseInfoAdvertType9UnitedParamsItemMenusItem,
        )
        from ..models.response_info_advert_type_9_united_params_item_subject import (
            ResponseInfoAdvertType9UnitedParamsItemSubject,
        )

        d = src_dict.copy()
        _subject = d.pop("subject", UNSET)
        subject: Union[Unset, ResponseInfoAdvertType9UnitedParamsItemSubject]
        if isinstance(_subject, Unset):
            subject = UNSET
        else:
            subject = ResponseInfoAdvertType9UnitedParamsItemSubject.from_dict(_subject)

        menus = []
        _menus = d.pop("menus", UNSET)
        for menus_item_data in _menus or []:
            menus_item = ResponseInfoAdvertType9UnitedParamsItemMenusItem.from_dict(menus_item_data)

            menus.append(menus_item)

        nms = cast(List[int], d.pop("nms", UNSET))

        search_cpm = d.pop("searchCPM", UNSET)

        catalog_cpm = d.pop("catalogCPM", UNSET)

        response_info_advert_type_9_united_params_item = cls(
            subject=subject,
            menus=menus,
            nms=nms,
            search_cpm=search_cpm,
            catalog_cpm=catalog_cpm,
        )

        response_info_advert_type_9_united_params_item.additional_properties = d
        return response_info_advert_type_9_united_params_item

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
