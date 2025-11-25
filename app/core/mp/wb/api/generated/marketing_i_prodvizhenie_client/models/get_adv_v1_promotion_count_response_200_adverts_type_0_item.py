from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item import (
        GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem,
    )


T = TypeVar("T", bound="GetAdvV1PromotionCountResponse200AdvertsType0Item")


@_attrs_define
class GetAdvV1PromotionCountResponse200AdvertsType0Item:
    """
    Attributes:
        type (Union[Unset, int]): Tip kampanii:
              - `4` — v kataloge (**ustarevshij tip**)
              - `5` — v kartochke tovara (**ustarevshij tip**)
              - `6` — v poiske (**ustarevshij tip**)
              - `7` — v rekomendatsijah na glavnoj stranitse (**ustarevshij tip**)
              - `8` — kampanija s edinoj stavkoj (**ustarevshij tip**)
              - `9` — kampanija s edinoj ili ruchnoj stavkoj. Tip stavki vy mozhete poluchit' s pomosch'ju metoda
            [Informatsija o kampanijah s ruchnoj stavkoj](./promotion#tag/Kampanii/paths/~1adv~1v0~1auction~1adverts/get),
            pole `bid_type`
        status (Union[Unset, int]): Status kampanii
        count (Union[Unset, int]): Kolichestvo kampanij
        advert_list (Union[Unset, List['GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem']]): Spisok
            kampanij
    """

    type: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    count: Union[Unset, int] = UNSET
    advert_list: Union[Unset, List["GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        type = self.type

        status = self.status

        count = self.count

        advert_list: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.advert_list, Unset):
            advert_list = []
            for advert_list_item_data in self.advert_list:
                advert_list_item = advert_list_item_data.to_dict()
                advert_list.append(advert_list_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if type is not UNSET:
            field_dict["type"] = type
        if status is not UNSET:
            field_dict["status"] = status
        if count is not UNSET:
            field_dict["count"] = count
        if advert_list is not UNSET:
            field_dict["advert_list"] = advert_list

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item import (
            GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem,
        )

        d = src_dict.copy()
        type = d.pop("type", UNSET)

        status = d.pop("status", UNSET)

        count = d.pop("count", UNSET)

        advert_list = []
        _advert_list = d.pop("advert_list", UNSET)
        for advert_list_item_data in _advert_list or []:
            advert_list_item = GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem.from_dict(
                advert_list_item_data
            )

            advert_list.append(advert_list_item)

        get_adv_v1_promotion_count_response_200_adverts_type_0_item = cls(
            type=type,
            status=status,
            count=count,
            advert_list=advert_list,
        )

        get_adv_v1_promotion_count_response_200_adverts_type_0_item.additional_properties = d
        return get_adv_v1_promotion_count_response_200_adverts_type_0_item

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
