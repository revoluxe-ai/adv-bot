from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostContentV2GetCardsTrashResponse200CardsItemWholesale")


@_attrs_define
class PostContentV2GetCardsTrashResponse200CardsItemWholesale:
    """Optovaja prodazha

    Attributes:
        enabled (bool | Unset): Prednaznachena li kartochka tovara dlja optovoj prodazhi
        quantum (float | Unset): Kolichestvo edinits tovara v upakovke
    """

    enabled: bool | Unset = UNSET
    quantum: float | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        enabled = self.enabled

        quantum = self.quantum

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if enabled is not UNSET:
            field_dict["enabled"] = enabled
        if quantum is not UNSET:
            field_dict["quantum"] = quantum

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        enabled = d.pop("enabled", UNSET)

        quantum = d.pop("quantum", UNSET)

        post_content_v2_get_cards_trash_response_200_cards_item_wholesale = cls(
            enabled=enabled,
            quantum=quantum,
        )

        post_content_v2_get_cards_trash_response_200_cards_item_wholesale.additional_properties = d
        return post_content_v2_get_cards_trash_response_200_cards_item_wholesale

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
