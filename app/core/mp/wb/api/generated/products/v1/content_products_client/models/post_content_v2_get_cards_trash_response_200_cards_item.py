from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.post_content_v2_get_cards_trash_response_200_cards_item_characteristics_type_0_item import (
        PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item,
    )
    from ..models.post_content_v2_get_cards_trash_response_200_cards_item_dimensions import (
        PostContentV2GetCardsTrashResponse200CardsItemDimensions,
    )
    from ..models.post_content_v2_get_cards_trash_response_200_cards_item_photos_item import (
        PostContentV2GetCardsTrashResponse200CardsItemPhotosItem,
    )
    from ..models.post_content_v2_get_cards_trash_response_200_cards_item_sizes_item import (
        PostContentV2GetCardsTrashResponse200CardsItemSizesItem,
    )
    from ..models.post_content_v2_get_cards_trash_response_200_cards_item_wholesale import (
        PostContentV2GetCardsTrashResponse200CardsItemWholesale,
    )


T = TypeVar("T", bound="PostContentV2GetCardsTrashResponse200CardsItem")


@_attrs_define
class PostContentV2GetCardsTrashResponse200CardsItem:
    """
    Attributes:
        nm_id (int | Unset): Artikul WB
        vendor_code (str | Unset): Artikul prodavtsa
        subject_id (int | Unset): ID predmeta
        subject_name (str | Unset): Nazvanie predmeta
        photos (list[PostContentV2GetCardsTrashResponse200CardsItemPhotosItem] | Unset): Massiv foto
        video (str | Unset): URL video
        wholesale (PostContentV2GetCardsTrashResponse200CardsItemWholesale | Unset): Optovaja prodazha
        sizes (list[PostContentV2GetCardsTrashResponse200CardsItemSizesItem] | Unset): Massiv razmerov
        dimensions (PostContentV2GetCardsTrashResponse200CardsItemDimensions | Unset): Gabarity i ves tovara c
            upakovkoj, sm i kg
        characteristics (list[PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item] | None | Unset):
            Harakteristiki
        created_at (str | Unset): Date and time the card was created
        trashed_at (str | Unset): Data i vremja pomeschenija v korzinu
    """

    nm_id: int | Unset = UNSET
    vendor_code: str | Unset = UNSET
    subject_id: int | Unset = UNSET
    subject_name: str | Unset = UNSET
    photos: list[PostContentV2GetCardsTrashResponse200CardsItemPhotosItem] | Unset = (
        UNSET
    )
    video: str | Unset = UNSET
    wholesale: PostContentV2GetCardsTrashResponse200CardsItemWholesale | Unset = UNSET
    sizes: list[PostContentV2GetCardsTrashResponse200CardsItemSizesItem] | Unset = UNSET
    dimensions: PostContentV2GetCardsTrashResponse200CardsItemDimensions | Unset = UNSET
    characteristics: (
        list[PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item]
        | None
        | Unset
    ) = UNSET
    created_at: str | Unset = UNSET
    trashed_at: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        nm_id = self.nm_id

        vendor_code = self.vendor_code

        subject_id = self.subject_id

        subject_name = self.subject_name

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

        sizes: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sizes, Unset):
            sizes = []
            for sizes_item_data in self.sizes:
                sizes_item = sizes_item_data.to_dict()
                sizes.append(sizes_item)

        dimensions: dict[str, Any] | Unset = UNSET
        if not isinstance(self.dimensions, Unset):
            dimensions = self.dimensions.to_dict()

        characteristics: list[dict[str, Any]] | None | Unset
        if isinstance(self.characteristics, Unset):
            characteristics = UNSET
        elif isinstance(self.characteristics, list):
            characteristics = []
            for characteristics_type_0_item_data in self.characteristics:
                characteristics_type_0_item = characteristics_type_0_item_data.to_dict()
                characteristics.append(characteristics_type_0_item)

        else:
            characteristics = self.characteristics

        created_at = self.created_at

        trashed_at = self.trashed_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if nm_id is not UNSET:
            field_dict["nmID"] = nm_id
        if vendor_code is not UNSET:
            field_dict["vendorCode"] = vendor_code
        if subject_id is not UNSET:
            field_dict["subjectID"] = subject_id
        if subject_name is not UNSET:
            field_dict["subjectName"] = subject_name
        if photos is not UNSET:
            field_dict["photos"] = photos
        if video is not UNSET:
            field_dict["video"] = video
        if wholesale is not UNSET:
            field_dict["wholesale"] = wholesale
        if sizes is not UNSET:
            field_dict["sizes"] = sizes
        if dimensions is not UNSET:
            field_dict["dimensions"] = dimensions
        if characteristics is not UNSET:
            field_dict["characteristics"] = characteristics
        if created_at is not UNSET:
            field_dict["createdAt"] = created_at
        if trashed_at is not UNSET:
            field_dict["trashedAt"] = trashed_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.post_content_v2_get_cards_trash_response_200_cards_item_characteristics_type_0_item import (
            PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item,
        )
        from ..models.post_content_v2_get_cards_trash_response_200_cards_item_dimensions import (
            PostContentV2GetCardsTrashResponse200CardsItemDimensions,
        )
        from ..models.post_content_v2_get_cards_trash_response_200_cards_item_photos_item import (
            PostContentV2GetCardsTrashResponse200CardsItemPhotosItem,
        )
        from ..models.post_content_v2_get_cards_trash_response_200_cards_item_sizes_item import (
            PostContentV2GetCardsTrashResponse200CardsItemSizesItem,
        )
        from ..models.post_content_v2_get_cards_trash_response_200_cards_item_wholesale import (
            PostContentV2GetCardsTrashResponse200CardsItemWholesale,
        )

        d = dict(src_dict)
        nm_id = d.pop("nmID", UNSET)

        vendor_code = d.pop("vendorCode", UNSET)

        subject_id = d.pop("subjectID", UNSET)

        subject_name = d.pop("subjectName", UNSET)

        _photos = d.pop("photos", UNSET)
        photos: (
            list[PostContentV2GetCardsTrashResponse200CardsItemPhotosItem] | Unset
        ) = UNSET
        if _photos is not UNSET:
            photos = []
            for photos_item_data in _photos:
                photos_item = (
                    PostContentV2GetCardsTrashResponse200CardsItemPhotosItem.from_dict(
                        photos_item_data
                    )
                )

                photos.append(photos_item)

        video = d.pop("video", UNSET)

        _wholesale = d.pop("wholesale", UNSET)
        wholesale: PostContentV2GetCardsTrashResponse200CardsItemWholesale | Unset
        if isinstance(_wholesale, Unset):
            wholesale = UNSET
        else:
            wholesale = (
                PostContentV2GetCardsTrashResponse200CardsItemWholesale.from_dict(
                    _wholesale
                )
            )

        _sizes = d.pop("sizes", UNSET)
        sizes: list[PostContentV2GetCardsTrashResponse200CardsItemSizesItem] | Unset = (
            UNSET
        )
        if _sizes is not UNSET:
            sizes = []
            for sizes_item_data in _sizes:
                sizes_item = (
                    PostContentV2GetCardsTrashResponse200CardsItemSizesItem.from_dict(
                        sizes_item_data
                    )
                )

                sizes.append(sizes_item)

        _dimensions = d.pop("dimensions", UNSET)
        dimensions: PostContentV2GetCardsTrashResponse200CardsItemDimensions | Unset
        if isinstance(_dimensions, Unset):
            dimensions = UNSET
        else:
            dimensions = (
                PostContentV2GetCardsTrashResponse200CardsItemDimensions.from_dict(
                    _dimensions
                )
            )

        def _parse_characteristics(
            data: object,
        ) -> (
            list[PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item]
            | None
            | Unset
        ):
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                characteristics_type_0 = []
                _characteristics_type_0 = data
                for characteristics_type_0_item_data in _characteristics_type_0:
                    characteristics_type_0_item = PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item.from_dict(
                        characteristics_type_0_item_data
                    )

                    characteristics_type_0.append(characteristics_type_0_item)

                return characteristics_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(
                list[
                    PostContentV2GetCardsTrashResponse200CardsItemCharacteristicsType0Item
                ]
                | None
                | Unset,
                data,
            )

        characteristics = _parse_characteristics(d.pop("characteristics", UNSET))

        created_at = d.pop("createdAt", UNSET)

        trashed_at = d.pop("trashedAt", UNSET)

        post_content_v2_get_cards_trash_response_200_cards_item = cls(
            nm_id=nm_id,
            vendor_code=vendor_code,
            subject_id=subject_id,
            subject_name=subject_name,
            photos=photos,
            video=video,
            wholesale=wholesale,
            sizes=sizes,
            dimensions=dimensions,
            characteristics=characteristics,
            created_at=created_at,
            trashed_at=trashed_at,
        )

        post_content_v2_get_cards_trash_response_200_cards_item.additional_properties = d
        return post_content_v2_get_cards_trash_response_200_cards_item

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
