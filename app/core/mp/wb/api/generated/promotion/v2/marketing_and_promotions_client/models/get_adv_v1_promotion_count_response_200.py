from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

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
        adverts (list[GetAdvV1PromotionCountResponse200AdvertsType0Item] | None | Unset): Dannye po kampanijam
        all_ (int | Unset): Obschee kolichestvo kampanij vseh statusov i tipov
    """

    adverts: list[GetAdvV1PromotionCountResponse200AdvertsType0Item] | None | Unset = (
        UNSET
    )
    all_: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        adverts: list[dict[str, Any]] | None | Unset
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

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if adverts is not UNSET:
            field_dict["adverts"] = adverts
        if all_ is not UNSET:
            field_dict["all"] = all_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_adv_v1_promotion_count_response_200_adverts_type_0_item import (
            GetAdvV1PromotionCountResponse200AdvertsType0Item,
        )

        d = dict(src_dict)

        def _parse_adverts(
            data: object,
        ) -> list[GetAdvV1PromotionCountResponse200AdvertsType0Item] | None | Unset:
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
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                list[GetAdvV1PromotionCountResponse200AdvertsType0Item] | None | Unset,
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
