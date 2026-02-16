from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_adv_v1_promotion_count_response_200_adverts_type_0_item import (
        GetAdvV1PromotionCountResponse200AdvertsType0Item,
    )


T = TypeVar("T", bound="GetAdvV1PromotionCountResponse200")


@_attrs_define
class GetAdvV1PromotionCountResponse200:
    """
    Attributes:
        adverts (Union[List['GetAdvV1PromotionCountResponse200AdvertsType0Item'], None, Unset]): Campaign data
        all_ (Union[Unset, int]): Total number of campaigns with all statuses and types
    """

    adverts: Union[
        List["GetAdvV1PromotionCountResponse200AdvertsType0Item"], None, Unset
    ] = UNSET
    all_: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        adverts: Union[List[Dict[str, Any]], None, Unset]
        if isinstance(self.adverts, Unset):
            adverts = UNSET
        elif isinstance(self.adverts, list):
            adverts = []
            for adverts_type_0_item_data in self.adverts:
                adverts_type_0_item = adverts_type_0_item_data.to_dict()
                adverts.append(adverts_type_0_item)

        else:
            adverts = self.adverts

        all_ = self.all_

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if adverts is not UNSET:
            field_dict["adverts"] = adverts
        if all_ is not UNSET:
            field_dict["all"] = all_

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.get_adv_v1_promotion_count_response_200_adverts_type_0_item import (
            GetAdvV1PromotionCountResponse200AdvertsType0Item,
        )

        d = src_dict.copy()

        def _parse_adverts(
            data: object,
        ) -> Union[
            List["GetAdvV1PromotionCountResponse200AdvertsType0Item"], None, Unset
        ]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                adverts_type_0 = []
                _adverts_type_0 = data
                for adverts_type_0_item_data in _adverts_type_0:
                    adverts_type_0_item = (
                        GetAdvV1PromotionCountResponse200AdvertsType0Item.from_dict(
                            adverts_type_0_item_data
                        )
                    )

                    adverts_type_0.append(adverts_type_0_item)

                return adverts_type_0
            except:  # noqa: E722
                pass
            return cast(
                Union[
                    List["GetAdvV1PromotionCountResponse200AdvertsType0Item"],
                    None,
                    Unset,
                ],
                data,
            )

        adverts = _parse_adverts(d.pop("adverts", UNSET))

        all_ = d.pop("all", UNSET)

        get_adv_v1_promotion_count_response_200 = cls(
            adverts=adverts,
            all_=all_,
        )

        get_adv_v1_promotion_count_response_200.additional_properties = d
        return get_adv_v1_promotion_count_response_200

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
