from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define

T = TypeVar("T", bound="RequestMoveNmsImtDisconn")


@_attrs_define
class RequestMoveNmsImtDisconn:
    """
    Attributes:
        nm_i_ds (list[int]): `nmID`, kotorye neobhodimo raz'edinit'
             Example: [837459235, 828572090].
    """

    nm_i_ds: list[int]

    def to_dict(self) -> dict[str, Any]:
        nm_i_ds = self.nm_i_ds

        field_dict: dict[str, Any] = {}

        field_dict.update(
            {
                "nmIDs": nm_i_ds,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        nm_i_ds = cast(list[int], d.pop("nmIDs"))

        request_move_nms_imt_disconn = cls(
            nm_i_ds=nm_i_ds,
        )

        return request_move_nms_imt_disconn
