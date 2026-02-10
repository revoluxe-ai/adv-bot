from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.size_good_req import SizeGoodReq


T = TypeVar("T", bound="PostApiV2UploadTaskSizeBody")


@_attrs_define
class PostApiV2UploadTaskSizeBody:
    """
    Attributes:
        data (list[SizeGoodReq]): Razmery i tseny dlja nih. Maksimum 1 000 razmerov.
            <br><br>
            Dlja tovarov s porazmernoj ustanovkoj tsen
            [karantin](https://seller.wildberries.ru/instructions/ru/ru/material/price-quarantine) ne primenjaetsja
    """

    data: list[SizeGoodReq]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = []
        for componentsschemas_size_goods_body_item_data in self.data:
            componentsschemas_size_goods_body_item = (
                componentsschemas_size_goods_body_item_data.to_dict()
            )
            data.append(componentsschemas_size_goods_body_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.size_good_req import SizeGoodReq

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for componentsschemas_size_goods_body_item_data in _data:
            componentsschemas_size_goods_body_item = SizeGoodReq.from_dict(
                componentsschemas_size_goods_body_item_data
            )

            data.append(componentsschemas_size_goods_body_item)

        post_api_v2_upload_task_size_body = cls(
            data=data,
        )

        post_api_v2_upload_task_size_body.additional_properties = d
        return post_api_v2_upload_task_size_body

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
