from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_cards_update_body_item_characteristics_item import (
        PostContentV2CardsUpdateBodyItemCharacteristicsItem,
    )
    from ..models.post_content_v2_cards_update_body_item_dimensions import (
        PostContentV2CardsUpdateBodyItemDimensions,
    )
    from ..models.post_content_v2_cards_update_body_item_sizes_item import (
        PostContentV2CardsUpdateBodyItemSizesItem,
    )


T = TypeVar("T", bound="PostContentV2CardsUpdateBodyItem")


@_attrs_define
class PostContentV2CardsUpdateBodyItem:
    """
    Attributes:
        nm_id (int): Artikul WB
        vendor_code (str): Artikul prodavtsa
        sizes (list[PostContentV2CardsUpdateBodyItemSizesItem]): Massiv razmerov<br>
            Dlja bezrazmernogo tovara vse ravno nuzhno peredavat' dannyj massiv bez parametrov (wbSize i techSize), no s
            barkodom
        brand (str | Unset): Brend
        title (str | Unset): Naimenovanie tovara
        description (str | Unset): Opisanie tovara<br>
            Maksimal'noe kolichestvo simvolov zavisit ot kategorii tovara<br>
            Standart — 2000, minimum — 1000, maksimum — 5000<br>
            Podrobno o pravilah opisanija v **Pravilah zapolnenija kartochki tovara** v [Spravochnom
            tsentre](https://seller.wildberries.ru/help-center/article/A-113) na portale prodavtsov
        dimensions (PostContentV2CardsUpdateBodyItemDimensions | Unset): Gabarity i ves tovara `c upakovkoj`.<br>
            Ukazhite v `santimetrah` i `kilogrammah` dlja ljubogo tovara.<br>
            Sinhronizatsija novyh dannyh s servisom mozhet zanimat' do 30 minut
        characteristics (list[PostContentV2CardsUpdateBodyItemCharacteristicsItem] | Unset): Harakteristiki tovara.
            <br>
            Mozhno poluchit' metodom [Harakteristiki predmeta](./work-with-products#tag/Kategorii-predmety-i-
            harakteristiki/paths/~1content~1v2~1object~1charcs~1%7BsubjectId%7D/get)
    """

    nm_id: int
    vendor_code: str
    sizes: list[PostContentV2CardsUpdateBodyItemSizesItem]
    brand: str | Unset = UNSET
    title: str | Unset = UNSET
    description: str | Unset = UNSET
    dimensions: PostContentV2CardsUpdateBodyItemDimensions | Unset = UNSET
    characteristics: (
        list[PostContentV2CardsUpdateBodyItemCharacteristicsItem] | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        vendor_code = self.vendor_code

        sizes = []
        for sizes_item_data in self.sizes:
            sizes_item = sizes_item_data.to_dict()
            sizes.append(sizes_item)

        brand = self.brand

        title = self.title

        description = self.description

        dimensions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.dimensions, Unset):
            dimensions = self.dimensions.to_dict()

        characteristics: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.characteristics, Unset):
            characteristics = []
            for characteristics_item_data in self.characteristics:
                characteristics_item = characteristics_item_data.to_dict()
                characteristics.append(characteristics_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "nmID": nm_id,
                "vendorCode": vendor_code,
                "sizes": sizes,
            }
        )
        if brand is not UNSET:
            field_dict["brand"] = brand
        if title is not UNSET:
            field_dict["title"] = title
        if description is not UNSET:
            field_dict["description"] = description
        if dimensions is not UNSET:
            field_dict["dimensions"] = dimensions
        if characteristics is not UNSET:
            field_dict["characteristics"] = characteristics

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_cards_update_body_item_characteristics_item import (
            PostContentV2CardsUpdateBodyItemCharacteristicsItem,
        )
        from ..models.post_content_v2_cards_update_body_item_dimensions import (
            PostContentV2CardsUpdateBodyItemDimensions,
        )
        from ..models.post_content_v2_cards_update_body_item_sizes_item import (
            PostContentV2CardsUpdateBodyItemSizesItem,
        )

        d = dict(src_dict)
        nm_id = d.pop("nmID")

        vendor_code = d.pop("vendorCode")

        sizes = []
        _sizes = d.pop("sizes")
        for sizes_item_data in _sizes:
            sizes_item = PostContentV2CardsUpdateBodyItemSizesItem.from_dict(
                sizes_item_data
            )

            sizes.append(sizes_item)

        brand = d.pop("brand", UNSET)

        title = d.pop("title", UNSET)

        description = d.pop("description", UNSET)

        _dimensions = d.pop("dimensions", UNSET)
        dimensions: PostContentV2CardsUpdateBodyItemDimensions | Unset
        if isinstance(_dimensions, Unset):
            dimensions = UNSET
        else:
            dimensions = PostContentV2CardsUpdateBodyItemDimensions.from_dict(
                _dimensions
            )

        _characteristics = d.pop("characteristics", UNSET)
        characteristics: (
            list[PostContentV2CardsUpdateBodyItemCharacteristicsItem] | Unset
        ) = UNSET
        if _characteristics is not UNSET:
            characteristics = []
            for characteristics_item_data in _characteristics:
                characteristics_item = (
                    PostContentV2CardsUpdateBodyItemCharacteristicsItem.from_dict(
                        characteristics_item_data
                    )
                )

                characteristics.append(characteristics_item)

        post_content_v2_cards_update_body_item = cls(
            nm_id=nm_id,
            vendor_code=vendor_code,
            sizes=sizes,
            brand=brand,
            title=title,
            description=description,
            dimensions=dimensions,
            characteristics=characteristics,
        )

        post_content_v2_cards_update_body_item.additional_properties = d
        return post_content_v2_cards_update_body_item

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
