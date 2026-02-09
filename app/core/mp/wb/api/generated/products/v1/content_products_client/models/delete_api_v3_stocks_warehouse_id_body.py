from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="DeleteApiV3StocksWarehouseIdBody")


@_attrs_define
class DeleteApiV3StocksWarehouseIdBody:
    """
    Attributes:
        chrt_ids (list[int]): Massiv ID razmerov tovarov
        skus (list[str] | Unset): Massiv barkodov. Parametr budet otkljuchen [9
            fevralja](https://dev.wildberries.ru/release-notes?id=386)
    """

    chrt_ids: list[int]
    skus: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        chrt_ids = self.chrt_ids

        skus: list[str] | Unset = UNSET
        if not isinstance(self.skus, Unset):
            skus = self.skus

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "chrtIds": chrt_ids,
            }
        )
        if skus is not UNSET:
            field_dict["skus"] = skus

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        chrt_ids = cast(list[int], d.pop("chrtIds"))

        skus = cast(list[str], d.pop("skus", UNSET))

        delete_api_v3_stocks_warehouse_id_body = cls(
            chrt_ids=chrt_ids,
            skus=skus,
        )

        delete_api_v3_stocks_warehouse_id_body.additional_properties = d
        return delete_api_v3_stocks_warehouse_id_body

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
