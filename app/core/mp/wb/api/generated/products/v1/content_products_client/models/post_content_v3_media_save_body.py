from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV3MediaSaveBody")


@_attrs_define
class PostContentV3MediaSaveBody:
    """
    Attributes:
        nm_id (int | Unset): Artikul WB
        data (list[str] | Unset): Ssylki na izobrazhenija v tom porjadke, v kotorom oni budut v kartochke tovara, i na
            video, na ljuboj pozitsii massiva
    """

    nm_id: int | Unset = UNSET
    data: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        data: list[str] | Unset = UNSET
        if not isinstance(self.data, Unset):
            data = self.data

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmId"] = nm_id
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmId", UNSET)

        data = cast(list[str], d.pop("data", UNSET))

        post_content_v3_media_save_body = cls(
            nm_id=nm_id,
            data=data,
        )

        post_content_v3_media_save_body.additional_properties = d
        return post_content_v3_media_save_body

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
