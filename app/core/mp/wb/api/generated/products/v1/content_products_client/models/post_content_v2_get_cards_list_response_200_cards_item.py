from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_get_cards_list_response_200_cards_item_characteristics_item import (
        PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem,
    )
    from ..models.post_content_v2_get_cards_list_response_200_cards_item_dimensions import (
        PostContentV2GetCardsListResponse200CardsItemDimensions,
    )
    from ..models.post_content_v2_get_cards_list_response_200_cards_item_photos_item import (
        PostContentV2GetCardsListResponse200CardsItemPhotosItem,
    )
    from ..models.post_content_v2_get_cards_list_response_200_cards_item_sizes_item import (
        PostContentV2GetCardsListResponse200CardsItemSizesItem,
    )
    from ..models.post_content_v2_get_cards_list_response_200_cards_item_tags_item import (
        PostContentV2GetCardsListResponse200CardsItemTagsItem,
    )
    from ..models.post_content_v2_get_cards_list_response_200_cards_item_wholesale import (
        PostContentV2GetCardsListResponse200CardsItemWholesale,
    )


T = TypeVar("T", bound="PostContentV2GetCardsListResponse200CardsItem")


@_attrs_define
class PostContentV2GetCardsListResponse200CardsItem:
    """
    Attributes:
        nm_id (int | Unset): Artikul WB
        imt_id (int | Unset): ID dlja [ob'edinennyh](https://dev.wildberries.ru/news/101#obuedinenie-i-razuedinenie-
            kartochek-tovarov) kartochek tovarov.<br>Edin dlja vseh artikulov WB gruppy ob'edinennyh kartochek.<br>U kazhdoj
            kartochki tovara est' `imtID`, dazhe esli ona ne ob'edinena s drugimi kartochkami<br>
        nm_uuid (str | Unset): Vnutrennij tehnicheskij ID kartochki tovara
        subject_id (int | Unset): ID predmeta
        subject_name (str | Unset): Nazvanie predmeta
        vendor_code (str | Unset): Artikul prodavtsa
        brand (str | Unset): Brend
        title (str | Unset): Naimenovanie tovara
        description (str | Unset): Opisanie tovara
        need_kiz (bool | Unset): Trebuetsja li [kod markirovki](https://chestnyjznak.rf/) dlja etogo tovara
            <br>
            * `false` — ne trebuetsja
            <br>
            * `true` — trebuetsja
        photos (list[PostContentV2GetCardsListResponse200CardsItemPhotosItem] | Unset): Massiv foto
        video (str | Unset): URL video
        wholesale (PostContentV2GetCardsListResponse200CardsItemWholesale | Unset): Optovaja prodazha
        dimensions (PostContentV2GetCardsListResponse200CardsItemDimensions | Unset): Gabarity i ves tovara c upakovkoj,
            sm i kg
        characteristics (list[PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem] | Unset): Harakteristiki
        sizes (list[PostContentV2GetCardsListResponse200CardsItemSizesItem] | Unset): Razmery tovara
        tags (list[PostContentV2GetCardsListResponse200CardsItemTagsItem] | Unset): Jarlyki
        created_at (str | Unset): Data i vremja sozdanija
        updated_at (str | Unset): Data i vremja izmenenija
    """

    nm_id: int | Unset = UNSET
    imt_id: int | Unset = UNSET
    nm_uuid: str | Unset = UNSET
    subject_id: int | Unset = UNSET
    subject_name: str | Unset = UNSET
    vendor_code: str | Unset = UNSET
    brand: str | Unset = UNSET
    title: str | Unset = UNSET
    description: str | Unset = UNSET
    need_kiz: bool | Unset = UNSET
    photos: list[PostContentV2GetCardsListResponse200CardsItemPhotosItem] | Unset = (
        UNSET
    )
    video: str | Unset = UNSET
    wholesale: PostContentV2GetCardsListResponse200CardsItemWholesale | Unset = UNSET
    dimensions: PostContentV2GetCardsListResponse200CardsItemDimensions | Unset = UNSET
    characteristics: (
        list[PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem] | Unset
    ) = UNSET
    sizes: list[PostContentV2GetCardsListResponse200CardsItemSizesItem] | Unset = UNSET
    tags: list[PostContentV2GetCardsListResponse200CardsItemTagsItem] | Unset = UNSET
    created_at: str | Unset = UNSET
    updated_at: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        imt_id = self.imt_id

        nm_uuid = self.nm_uuid

        subject_id = self.subject_id

        subject_name = self.subject_name

        vendor_code = self.vendor_code

        brand = self.brand

        title = self.title

        description = self.description

        need_kiz = self.need_kiz

        photos: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.photos, Unset):
            photos = []
            for photos_item_data in self.photos:
                photos_item = photos_item_data.to_dict()
                photos.append(photos_item)

        video = self.video

        wholesale: dict[str, Any] | Unset = UNSET
        if not isinstance(self.wholesale, Unset):
            wholesale = self.wholesale.to_dict()

        dimensions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.dimensions, Unset):
            dimensions = self.dimensions.to_dict()

        characteristics: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.characteristics, Unset):
            characteristics = []
            for characteristics_item_data in self.characteristics:
                characteristics_item = characteristics_item_data.to_dict()
                characteristics.append(characteristics_item)

        sizes: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sizes, Unset):
            sizes = []
            for sizes_item_data in self.sizes:
                sizes_item = sizes_item_data.to_dict()
                sizes.append(sizes_item)

        tags: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.tags, Unset):
            tags = []
            for tags_item_data in self.tags:
                tags_item = tags_item_data.to_dict()
                tags.append(tags_item)

        created_at = self.created_at

        updated_at = self.updated_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if imt_id is not UNSET:
            field_dict["imtID"] = imt_id
        if nm_uuid is not UNSET:
            field_dict["nmUUID"] = nm_uuid
        if subject_id is not UNSET:
            field_dict["subjectID"] = subject_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if brand is not UNSET:
            field_dict["brand"] = brand
        if title is not UNSET:
            field_dict["title"] = title
        if description is not UNSET:
            field_dict["description"] = description
        if need_kiz is not UNSET:
            field_dict["needKiz"] = need_kiz
        if photos is not UNSET:
            field_dict["photos"] = photos
        if video is not UNSET:
            field_dict["video"] = video
        if wholesale is not UNSET:
            field_dict["wholesale"] = wholesale
        if dimensions is not UNSET:
            field_dict["dimensions"] = dimensions
        if characteristics is not UNSET:
            field_dict["characteristics"] = characteristics
        if sizes is not UNSET:
            field_dict["sizes"] = sizes
        if tags is not UNSET:
            field_dict["tags"] = tags
        if created_at is not UNSET:
            field_dict["createdAt"] = created_at
        if updated_at is not UNSET:
            field_dict["updatedAt"] = updated_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_get_cards_list_response_200_cards_item_characteristics_item import (
            PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem,
        )
        from ..models.post_content_v2_get_cards_list_response_200_cards_item_dimensions import (
            PostContentV2GetCardsListResponse200CardsItemDimensions,
        )
        from ..models.post_content_v2_get_cards_list_response_200_cards_item_photos_item import (
            PostContentV2GetCardsListResponse200CardsItemPhotosItem,
        )
        from ..models.post_content_v2_get_cards_list_response_200_cards_item_sizes_item import (
            PostContentV2GetCardsListResponse200CardsItemSizesItem,
        )
        from ..models.post_content_v2_get_cards_list_response_200_cards_item_tags_item import (
            PostContentV2GetCardsListResponse200CardsItemTagsItem,
        )
        from ..models.post_content_v2_get_cards_list_response_200_cards_item_wholesale import (
            PostContentV2GetCardsListResponse200CardsItemWholesale,
        )

        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        imt_id = d.pop("imtID", UNSET)

        nm_uuid = d.pop("nmUUID", UNSET)

        subject_id = d.pop("subjectID", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        brand = d.pop("brand", UNSET)

        title = d.pop("title", UNSET)

        description = d.pop("description", UNSET)

        need_kiz = d.pop("needKiz", UNSET)

        _photos = d.pop("photos", UNSET)
        photos: (
            list[PostContentV2GetCardsListResponse200CardsItemPhotosItem] | Unset
        ) = UNSET
        if _photos is not UNSET:
            photos = []
            for photos_item_data in _photos:
                photos_item = (
                    PostContentV2GetCardsListResponse200CardsItemPhotosItem.from_dict(
                        photos_item_data
                    )
                )

                photos.append(photos_item)

        video = d.pop("video", UNSET)

        _wholesale = d.pop("wholesale", UNSET)
        wholesale: PostContentV2GetCardsListResponse200CardsItemWholesale | Unset
        if isinstance(_wholesale, Unset):
            wholesale = UNSET
        else:
            wholesale = (
                PostContentV2GetCardsListResponse200CardsItemWholesale.from_dict(
                    _wholesale
                )
            )

        _dimensions = d.pop("dimensions", UNSET)
        dimensions: PostContentV2GetCardsListResponse200CardsItemDimensions | Unset
        if isinstance(_dimensions, Unset):
            dimensions = UNSET
        else:
            dimensions = (
                PostContentV2GetCardsListResponse200CardsItemDimensions.from_dict(
                    _dimensions
                )
            )

        _characteristics = d.pop("characteristics", UNSET)
        characteristics: (
            list[PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem]
            | Unset
        ) = UNSET
        if _characteristics is not UNSET:
            characteristics = []
            for characteristics_item_data in _characteristics:
                characteristics_item = PostContentV2GetCardsListResponse200CardsItemCharacteristicsItem.from_dict(
                    characteristics_item_data
                )

                characteristics.append(characteristics_item)

        _sizes = d.pop("sizes", UNSET)
        sizes: list[PostContentV2GetCardsListResponse200CardsItemSizesItem] | Unset = (
            UNSET
        )
        if _sizes is not UNSET:
            sizes = []
            for sizes_item_data in _sizes:
                sizes_item = (
                    PostContentV2GetCardsListResponse200CardsItemSizesItem.from_dict(
                        sizes_item_data
                    )
                )

                sizes.append(sizes_item)

        _tags = d.pop("tags", UNSET)
        tags: list[PostContentV2GetCardsListResponse200CardsItemTagsItem] | Unset = (
            UNSET
        )
        if _tags is not UNSET:
            tags = []
            for tags_item_data in _tags:
                tags_item = (
                    PostContentV2GetCardsListResponse200CardsItemTagsItem.from_dict(
                        tags_item_data
                    )
                )

                tags.append(tags_item)

        created_at = d.pop("createdAt", UNSET)

        updated_at = d.pop("updatedAt", UNSET)

        post_content_v2_get_cards_list_response_200_cards_item = cls(
            nm_id=nm_id,
            imt_id=imt_id,
            nm_uuid=nm_uuid,
            subject_id=subject_id,
            subject_name=subject_name,
            vendor_code=vendor_code,
            brand=brand,
            title=title,
            description=description,
            need_kiz=need_kiz,
            photos=photos,
            video=video,
            wholesale=wholesale,
            dimensions=dimensions,
            characteristics=characteristics,
            sizes=sizes,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at,
        )

        post_content_v2_get_cards_list_response_200_cards_item.additional_properties = d
        return post_content_v2_get_cards_list_response_200_cards_item

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
