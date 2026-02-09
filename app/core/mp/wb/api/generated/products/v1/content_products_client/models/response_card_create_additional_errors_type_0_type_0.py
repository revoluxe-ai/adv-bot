from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ResponseCardCreateAdditionalErrorsType0Type0")


@_attrs_define
class ResponseCardCreateAdditionalErrorsType0Type0:
    """
    Attributes:
        string (str | Unset):
    """

    string: str | Unset = UNSET

    def to_dict(self) -> dict[str, Any]:
        string = self.string

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if string is not UNSET:
            field_dict["string"] = string

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        string = d.pop("string", UNSET)

        response_card_create_additional_errors_type_0_type_0 = cls(
            string=string,
        )

        return response_card_create_additional_errors_type_0_type_0
