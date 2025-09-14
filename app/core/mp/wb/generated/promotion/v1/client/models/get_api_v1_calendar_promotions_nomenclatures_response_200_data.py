from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.promotions_goods_list import PromotionsGoodsList


T = TypeVar("T", bound="GetApiV1CalendarPromotionsNomenclaturesResponse200Data")


@_attrs_define
class GetApiV1CalendarPromotionsNomenclaturesResponse200Data:
    """
    Attributes:
        nomenclatures (Union[Unset, list['PromotionsGoodsList']]):
    """

    nomenclatures: Union[Unset, list["PromotionsGoodsList"]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nomenclatures: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.nomenclatures, Unset):
            nomenclatures = []
            for nomenclatures_item_data in self.nomenclatures:
                nomenclatures_item = nomenclatures_item_data.to_dict()
                nomenclatures.append(nomenclatures_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nomenclatures is not UNSET:
            field_dict["nomenclatures"] = nomenclatures

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.promotions_goods_list import PromotionsGoodsList

        d = dict(src_dict)
        nomenclatures = []
        _nomenclatures = d.pop("nomenclatures", UNSET)
        for nomenclatures_item_data in _nomenclatures or []:
            nomenclatures_item = PromotionsGoodsList.from_dict(nomenclatures_item_data)

            nomenclatures.append(nomenclatures_item)

        get_api_v1_calendar_promotions_nomenclatures_response_200_data = cls(
            nomenclatures=nomenclatures,
        )

        get_api_v1_calendar_promotions_nomenclatures_response_200_data.additional_properties = d
        return get_api_v1_calendar_promotions_nomenclatures_response_200_data

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
