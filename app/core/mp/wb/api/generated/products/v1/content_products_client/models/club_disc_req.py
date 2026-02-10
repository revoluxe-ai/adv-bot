from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ClubDiscReq")


@_attrs_define
class ClubDiscReq:
    """
    Attributes:
        nm_id (int): Artikul WB Example: 123.
        club_discount (int): Skidka WB Kluba, % Example: 5.
    """

    nm_id: int
    club_discount: int
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        club_discount = self.club_discount

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmID": nm_id,
                "clubDiscount": club_discount,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_id = d.pop("nmID")

        club_discount = d.pop("clubDiscount")

        club_disc_req = cls(
            nm_id=nm_id,
            club_discount=club_discount,
        )

        club_disc_req.additional_properties = d
        return club_disc_req

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
