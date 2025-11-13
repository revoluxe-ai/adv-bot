from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseInfoAdvertType8AutoParamsNmCPMItem")


@_attrs_define
class ResponseInfoAdvertType8AutoParamsNmCPMItem:
    """
    Attributes:
        nm (Union[Unset, int]): Artikul WB
        cpm (Union[Unset, int]): Stavka
    """

    nm: Union[Unset, int] = UNSET
    cpm: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        nm = self.nm

        cpm = self.cpm

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm is not UNSET:
            field_dict["nm"] = nm
        if cpm is not UNSET:
            field_dict["cpm"] = cpm

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        nm = d.pop("nm", UNSET)

        cpm = d.pop("cpm", UNSET)

        response_info_advert_type_8_auto_params_nm_cpm_item = cls(
            nm=nm,
            cpm=cpm,
        )

        response_info_advert_type_8_auto_params_nm_cpm_item.additional_properties = d
        return response_info_advert_type_8_auto_params_nm_cpm_item

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
