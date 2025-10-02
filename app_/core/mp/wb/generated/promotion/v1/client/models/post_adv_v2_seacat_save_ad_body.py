from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV2SeacatSaveAdBody")


@_attrs_define
class PostAdvV2SeacatSaveAdBody:
    """
    Attributes:
        name (Union[Unset, str]): Nazvanie kampanii
        nms (Union[Unset, list[int]]): Kartochki tovarov dlja kampanii. Dostupnye kartochki tovarov mozhno poluchit' s
            pomosch'ju metoda [Kartochki tovarov dlja kampanij](./promotion#tag/Sozdanie-
            kampanij/paths/~1adv~1v2~1supplier~1nms/post). Maksimum 50 tovarov (`nm`)
    """

    name: Union[Unset, str] = UNSET
    nms: Union[Unset, list[int]] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        nms: Union[Unset, list[int]] = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if name is not UNSET:
            field_dict["name"] = name
        if nms is not UNSET:
            field_dict["nms"] = nms

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name", UNSET)

        nms = cast(list[int], d.pop("nms", UNSET))

        post_adv_v2_seacat_save_ad_body = cls(
            name=name,
            nms=nms,
        )

        post_adv_v2_seacat_save_ad_body.additional_properties = d
        return post_adv_v2_seacat_save_ad_body

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
