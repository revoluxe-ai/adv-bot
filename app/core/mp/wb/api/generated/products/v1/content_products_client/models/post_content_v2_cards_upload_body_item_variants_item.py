from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_cards_upload_body_item_variants_item_characteristics_item import (
        PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem,
    )
    from ..models.post_content_v2_cards_upload_body_item_variants_item_dimensions import (
        PostContentV2CardsUploadBodyItemVariantsItemDimensions,
    )
    from ..models.post_content_v2_cards_upload_body_item_variants_item_sizes_item import (
        PostContentV2CardsUploadBodyItemVariantsItemSizesItem,
    )
    from ..models.post_content_v2_cards_upload_body_item_variants_item_wholesale import (
        PostContentV2CardsUploadBodyItemVariantsItemWholesale,
    )


T = TypeVar("T", bound="PostContentV2CardsUploadBodyItemVariantsItem")


@_attrs_define
class PostContentV2CardsUploadBodyItemVariantsItem:
    """
    Attributes:
        vendor_code (str): Artikul prodavtsa
        brand (str | Unset): Brend
        title (str | Unset): Naimenovanie tovara
        description (str | Unset): Opisanie tovara.<br>
            Maksimal'noe kolichestvo simvolov zavisit ot kategorii tovara<br>
            Standart — 2000, minimum — 1000, maksimum — 5000<br>
            Podrobno o pravilah opisanija v **Pravilah zapolnenija kartochki tovara** v razdele v [Spravochnom
            tsentre](https://seller.wildberries.ru/help-center/article/A-113) na portale prodavtsov
        wholesale (PostContentV2CardsUploadBodyItemVariantsItemWholesale | Unset): Optovaja prodazha
        dimensions (PostContentV2CardsUploadBodyItemVariantsItemDimensions | Unset): Gabarity i ves tovara `c
            upakovkoj`.<br>
            Ukazhite v `santimetrah` i `kilogrammah` dlja ljubogo tovara.<br>
            Esli dannye ne ukazany, avtomaticheski sgenerirujutsja nulevye znachenija dliny, shiriny, vysoty i vesa.<br>
            Sinhronizatsija dannyh novoj kartochki s servisom mozhet zanimat' do 30 minut
        sizes (list[PostContentV2CardsUploadBodyItemVariantsItemSizesItem] | Unset): Massiv razmerov.<br>
            Esli ne ukazat' dlja razmernogo tovara (obuv', odezhda i dr.), sgeneriruetsja avtomaticheski s `techSize` = "A",
            `wbSize` = "1" i barkodom
        characteristics (list[PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem] | Unset): Harakteristiki
            tovara.
            <br>
            Mozhno poluchit' metodom [Harakteristiki predmeta](./work-with-products#tag/Kategorii-predmety-i-
            harakteristiki/paths/~1content~1v2~1object~1charcs~1%7BsubjectId%7D/get)
    """

    vendor_code: str
    brand: str | Unset = UNSET
    title: str | Unset = UNSET
    description: str | Unset = UNSET
    wholesale: PostContentV2CardsUploadBodyItemVariantsItemWholesale | Unset = UNSET
    dimensions: PostContentV2CardsUploadBodyItemVariantsItemDimensions | Unset = UNSET
    sizes: list[PostContentV2CardsUploadBodyItemVariantsItemSizesItem] | Unset = UNSET
    characteristics: (
        list[PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem] | Unset
    ) = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        vendor_code = self.vendor_code

        brand = self.brand

        title = self.title

        description = self.description

        wholesale: dict[str, Any] | Unset = UNSET
        if not isinstance(self.wholesale, Unset):
            wholesale = self.wholesale.to_dict()

        dimensions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.dimensions, Unset):
            dimensions = self.dimensions.to_dict()

        sizes: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sizes, Unset):
            sizes = []
            for sizes_item_data in self.sizes:
                sizes_item = sizes_item_data.to_dict()
                sizes.append(sizes_item)

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
                "vendorCode": vendor_code,
            }
        )
        if brand is not UNSET:
            field_dict["brand"] = brand
        if title is not UNSET:
            field_dict["title"] = title
        if description is not UNSET:
            field_dict["description"] = description
        if wholesale is not UNSET:
            field_dict["wholesale"] = wholesale
        if dimensions is not UNSET:
            field_dict["dimensions"] = dimensions
        if sizes is not UNSET:
            field_dict["sizes"] = sizes
        if characteristics is not UNSET:
            field_dict["characteristics"] = characteristics

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_cards_upload_body_item_variants_item_characteristics_item import (
            PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem,
        )
        from ..models.post_content_v2_cards_upload_body_item_variants_item_dimensions import (
            PostContentV2CardsUploadBodyItemVariantsItemDimensions,
        )
        from ..models.post_content_v2_cards_upload_body_item_variants_item_sizes_item import (
            PostContentV2CardsUploadBodyItemVariantsItemSizesItem,
        )
        from ..models.post_content_v2_cards_upload_body_item_variants_item_wholesale import (
            PostContentV2CardsUploadBodyItemVariantsItemWholesale,
        )

        d = dict(src_dict)
        vendor_code = d.pop("vendorCode")

        brand = d.pop("brand", UNSET)

        title = d.pop("title", UNSET)

        description = d.pop("description", UNSET)

        _wholesale = d.pop("wholesale", UNSET)
        wholesale: PostContentV2CardsUploadBodyItemVariantsItemWholesale | Unset
        if isinstance(_wholesale, Unset):
            wholesale = UNSET
        else:
            wholesale = PostContentV2CardsUploadBodyItemVariantsItemWholesale.from_dict(
                _wholesale
            )

        _dimensions = d.pop("dimensions", UNSET)
        dimensions: PostContentV2CardsUploadBodyItemVariantsItemDimensions | Unset
        if isinstance(_dimensions, Unset):
            dimensions = UNSET
        else:
            dimensions = (
                PostContentV2CardsUploadBodyItemVariantsItemDimensions.from_dict(
                    _dimensions
                )
            )

        _sizes = d.pop("sizes", UNSET)
        sizes: list[PostContentV2CardsUploadBodyItemVariantsItemSizesItem] | Unset = (
            UNSET
        )
        if _sizes is not UNSET:
            sizes = []
            for sizes_item_data in _sizes:
                sizes_item = (
                    PostContentV2CardsUploadBodyItemVariantsItemSizesItem.from_dict(
                        sizes_item_data
                    )
                )

                sizes.append(sizes_item)

        _characteristics = d.pop("characteristics", UNSET)
        characteristics: (
            list[PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem]
            | Unset
        ) = UNSET
        if _characteristics is not UNSET:
            characteristics = []
            for characteristics_item_data in _characteristics:
                characteristics_item = PostContentV2CardsUploadBodyItemVariantsItemCharacteristicsItem.from_dict(
                    characteristics_item_data
                )

                characteristics.append(characteristics_item)

        post_content_v2_cards_upload_body_item_variants_item = cls(
            vendor_code=vendor_code,
            brand=brand,
            title=title,
            description=description,
            wholesale=wholesale,
            dimensions=dimensions,
            sizes=sizes,
            characteristics=characteristics,
        )

        post_content_v2_cards_upload_body_item_variants_item.additional_properties = d
        return post_content_v2_cards_upload_body_item_variants_item

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
