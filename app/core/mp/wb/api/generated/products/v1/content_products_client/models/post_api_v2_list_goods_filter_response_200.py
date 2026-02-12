from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.post_api_v2_list_goods_filter_response_200_data import (
        PostApiV2ListGoodsFilterResponse200Data,
    )


T = TypeVar("T", bound="PostApiV2ListGoodsFilterResponse200")


@_attrs_define
class PostApiV2ListGoodsFilterResponse200:
    """
    Attributes:
        data (PostApiV2ListGoodsFilterResponse200Data): Dannye otveta
        error (bool): Flag oshibki
        error_text (str): Tekst oshibki
    """

    data: PostApiV2ListGoodsFilterResponse200Data
    error: bool
    error_text: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = self.data.to_dict()

        error = self.error

        error_text = self.error_text

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
                "error": error,
                "errorText": error_text,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_api_v2_list_goods_filter_response_200_data import (
            PostApiV2ListGoodsFilterResponse200Data,
        )

        d = dict(src_dict)
        data = PostApiV2ListGoodsFilterResponse200Data.from_dict(d.pop("data"))

        error = d.pop("error")

        error_text = d.pop("errorText")

        post_api_v2_list_goods_filter_response_200 = cls(
            data=data,
            error=error,
            error_text=error_text,
        )

        post_api_v2_list_goods_filter_response_200.additional_properties = d
        return post_api_v2_list_goods_filter_response_200

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
