from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.brands_response_brands_item import BrandsResponseBrandsItem


T = TypeVar("T", bound="BrandsResponse")


@_attrs_define
class BrandsResponse:
    """
    Attributes:
        brands (list[BrandsResponseBrandsItem]):
        total (int): Obschee kolichestvo brendov predmeta Example: 344534.
        next_ (int | Unset): Parametr paginatsii. Ukazhite eto znachenie v zaprose, chtoby poluchit' sledujuschij paket
            dannyh. Esli pole otsutstvuet, vy poluchili vse dannye Example: 1212.
    """

    brands: list[BrandsResponseBrandsItem]
    total: int
    next_: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        brands = []
        for brands_item_data in self.brands:
            brands_item = brands_item_data.to_dict()
            brands.append(brands_item)

        total = self.total

        next_ = self.next_

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "brands": brands,
                "total": total,
            }
        )
        if next_ is not UNSET:
            field_dict["next"] = next_

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.brands_response_brands_item import BrandsResponseBrandsItem

        d = dict(src_dict)
        brands = []
        _brands = d.pop("brands")
        for brands_item_data in _brands:
            brands_item = BrandsResponseBrandsItem.from_dict(brands_item_data)

            brands.append(brands_item)

        total = d.pop("total")

        next_ = d.pop("next", UNSET)

        brands_response = cls(
            brands=brands,
            total=total,
            next_=next_,
        )

        brands_response.additional_properties = d
        return brands_response

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
