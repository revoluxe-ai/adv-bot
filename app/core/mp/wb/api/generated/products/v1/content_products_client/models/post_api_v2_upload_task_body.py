from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.good import Good


T = TypeVar("T", bound="PostApiV2UploadTaskBody")


@_attrs_define
class PostApiV2UploadTaskBody:
    """
    Attributes:
        data (list[Good]): Tovary, tseny i skidki dlja nih. Maksimum 1 000 tovarov. Tsena i skidka ne mogut byt' pustymi
            odnovremenno.
            <br><br>
            Esli novaja tsena so skidkoj budet hotja by v 3 raza men'she staroj, ona popadet
            v [karantin](https://seller.wildberries.ru/instructions/ru/ru/material/price-quarantine) i tovar budet
            prodavat'sja po staroj tsene. Oshibka ob etom budet v otvetah metodov sostojanij zagruzok.
            <br><br>
            Vy mozhete izmenit' tsenu ili skidku s pomosch'ju API libo vyvesti tovar iz karantina v [lichnom
            kabinete](https://seller.wildberries.ru/discount-and-prices/quarantine)
    """

    data: list[Good]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = []
        for componentsschemas_goods_item_data in self.data:
            componentsschemas_goods_item = componentsschemas_goods_item_data.to_dict()
            data.append(componentsschemas_goods_item)

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
        from ..models.good import Good

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for componentsschemas_goods_item_data in _data:
            componentsschemas_goods_item = Good.from_dict(
                componentsschemas_goods_item_data
            )

            data.append(componentsschemas_goods_item)

        post_api_v2_upload_task_body = cls(
            data=data,
        )

        post_api_v2_upload_task_body.additional_properties = d
        return post_api_v2_upload_task_body

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
