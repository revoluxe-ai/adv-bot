from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.put_api_v3_stocks_warehouse_id_response_406_data_type_0 import (
        PutApiV3StocksWarehouseIdResponse406DataType0,
    )


T = TypeVar("T", bound="PutApiV3StocksWarehouseIdResponse406")


@_attrs_define
class PutApiV3StocksWarehouseIdResponse406:
    """
    Attributes:
        code (str | Unset): Kod oshibki Example: StatusNotAcceptable.
        message (str | Unset): Opisanie oshibki Example: Obnovlenie ostatkov zablokirovano v svjazi s banom
            postavschika.
        data (None | PutApiV3StocksWarehouseIdResponse406DataType0 | Unset): Dopolnitel'nye dannye oshibki
    """

    code: str | Unset = UNSET
    message: str | Unset = UNSET
    data: None | PutApiV3StocksWarehouseIdResponse406DataType0 | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.put_api_v3_stocks_warehouse_id_response_406_data_type_0 import (
            PutApiV3StocksWarehouseIdResponse406DataType0,
        )

        code = self.code

        message = self.message

        data: dict[str, Any] | None | Unset
        if isinstance(self.data, Unset):
            data = UNSET
        elif isinstance(self.data, PutApiV3StocksWarehouseIdResponse406DataType0):
            data = self.data.to_dict()
        else:
            data = self.data

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if code is not UNSET:
            field_dict["code"] = code
        if message is not UNSET:
            field_dict["message"] = message
        if data is not UNSET:
            field_dict["data"] = data

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.put_api_v3_stocks_warehouse_id_response_406_data_type_0 import (
            PutApiV3StocksWarehouseIdResponse406DataType0,
        )

        d = dict(src_dict)
        code = d.pop("code", UNSET)

        message = d.pop("message", UNSET)

        def _parse_data(
            data: object,
        ) -> None | PutApiV3StocksWarehouseIdResponse406DataType0 | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                data_type_0 = PutApiV3StocksWarehouseIdResponse406DataType0.from_dict(
                    data
                )

                return data_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                None | PutApiV3StocksWarehouseIdResponse406DataType0 | Unset, data
            )

        data = _parse_data(d.pop("data", UNSET))

        put_api_v3_stocks_warehouse_id_response_406 = cls(
            code=code,
            message=message,
            data=data,
        )

        put_api_v3_stocks_warehouse_id_response_406.additional_properties = d
        return put_api_v3_stocks_warehouse_id_response_406

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
