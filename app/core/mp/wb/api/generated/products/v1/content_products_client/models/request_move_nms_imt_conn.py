from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RequestMoveNmsImtConn")


@_attrs_define
class RequestMoveNmsImtConn:
    """
    Attributes:
        target_imt (int): Suschestvujuschij `imtID`, pod kotorym neobhodimo
            [ob'edinit'](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-kartochek-tovarov) kartochki tovarov
            Example: 123.
        nm_i_ds (list[int]): `nmID`, kotorye neobhodimo ob'edinit'
             Example: [837459235, 828572090].
    """

    target_imt: int
    nm_i_ds: list[int]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        target_imt = self.target_imt

        nm_i_ds = self.nm_i_ds

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "targetIMT": target_imt,
                "nmIDs": nm_i_ds,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        target_imt = d.pop("targetIMT")

        nm_i_ds = cast(list[int], d.pop("nmIDs"))

        request_move_nms_imt_conn = cls(
            target_imt=target_imt,
            nm_i_ds=nm_i_ds,
        )

        request_move_nms_imt_conn.additional_properties = d
        return request_move_nms_imt_conn

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
