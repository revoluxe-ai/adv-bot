from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2TagNomenclatureLinkBody")


@_attrs_define
class PostContentV2TagNomenclatureLinkBody:
    """
    Attributes:
        nm_id (int | Unset): Artikul WB
        tags_i_ds (list[int] | Unset): Massiv chislovyh ID jarlykov.<br>
            Chto by snjat' jarlyki s kartochki tovara, neobhodimo peredat' pustoj massiv.<br>
            Chtoby dobavit' jarlyki k uzhe imejuschimsja v kartochke tovara, neobhodimo v zaprose peredat' novye jarlyki i
            jarlyki, kotorye uzhe est' v kartochke tovara.
    """

    nm_id: int | Unset = UNSET
    tags_i_ds: list[int] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        tags_i_ds: list[int] | Unset = UNSET
        if not isinstance(self.tags_i_ds, Unset):
            tags_i_ds = self.tags_i_ds

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if tags_i_ds is not UNSET:
            field_dict["tagsIDs"] = tags_i_ds

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        tags_i_ds = cast(list[int], d.pop("tagsIDs", UNSET))

        post_content_v2_tag_nomenclature_link_body = cls(
            nm_id=nm_id,
            tags_i_ds=tags_i_ds,
        )

        post_content_v2_tag_nomenclature_link_body.additional_properties = d
        return post_content_v2_tag_nomenclature_link_body

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
