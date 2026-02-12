from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.good_buffer_history import GoodBufferHistory


T = TypeVar("T", bound="GetApiV2BufferGoodsTaskResponse200Data")


@_attrs_define
class GetApiV2BufferGoodsTaskResponse200Data:
    """Dannye otveta

    Attributes:
        upload_id (int | None | Unset): ID zagruzki Example: 3235236546.
        buffer_goods (list[GoodBufferHistory] | None | Unset): Informatsija o tovarah v zagruzke
    """

    upload_id: int | None | Unset = UNSET
    buffer_goods: list[GoodBufferHistory] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        upload_id: int | None | Unset
        if isinstance(self.upload_id, Unset):
            upload_id = UNSET
        else:
            upload_id = self.upload_id

        buffer_goods: list[dict[str, Any]] | None | Unset
        if isinstance(self.buffer_goods, Unset):
            buffer_goods = UNSET
        elif isinstance(self.buffer_goods, list):
            buffer_goods = []
            for buffer_goods_type_0_item_data in self.buffer_goods:
                buffer_goods_type_0_item = buffer_goods_type_0_item_data.to_dict()
                buffer_goods.append(buffer_goods_type_0_item)

        else:
            buffer_goods = self.buffer_goods

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if upload_id is not UNSET:
            field_dict["uploadID"] = upload_id
        if buffer_goods is not UNSET:
            field_dict["bufferGoods"] = buffer_goods

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.good_buffer_history import GoodBufferHistory

        d = dict(src_dict)

        def _parse_upload_id(data: object) -> int | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(int | None | Unset, data)

        upload_id = _parse_upload_id(d.pop("uploadID", UNSET))

        def _parse_buffer_goods(data: object) -> list[GoodBufferHistory] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                buffer_goods_type_0 = []
                _buffer_goods_type_0 = data
                for buffer_goods_type_0_item_data in _buffer_goods_type_0:
                    buffer_goods_type_0_item = GoodBufferHistory.from_dict(
                        buffer_goods_type_0_item_data
                    )

                    buffer_goods_type_0.append(buffer_goods_type_0_item)

                return buffer_goods_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[GoodBufferHistory] | None | Unset, data)

        buffer_goods = _parse_buffer_goods(d.pop("bufferGoods", UNSET))

        get_api_v2_buffer_goods_task_response_200_data = cls(
            upload_id=upload_id,
            buffer_goods=buffer_goods,
        )

        get_api_v2_buffer_goods_task_response_200_data.additional_properties = d
        return get_api_v2_buffer_goods_task_response_200_data

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
