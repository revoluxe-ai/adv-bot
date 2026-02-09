from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.models_error_table_list_public_resp_v2_item_brands import (
        ModelsErrorTableListPublicRespV2ItemBrands,
    )
    from ..models.models_error_table_list_public_resp_v2_item_errors import (
        ModelsErrorTableListPublicRespV2ItemErrors,
    )
    from ..models.models_error_table_list_public_resp_v2_item_subjects import (
        ModelsErrorTableListPublicRespV2ItemSubjects,
    )


T = TypeVar("T", bound="ModelsErrorTableListPublicRespV2Item")


@_attrs_define
class ModelsErrorTableListPublicRespV2Item:
    """
    Attributes:
        batch_uuid (str): ID paketa
        subjects (ModelsErrorTableListPublicRespV2ItemSubjects): Predmety. Razbivka po `vendorCodes`
        brands (ModelsErrorTableListPublicRespV2ItemBrands): Brendy. Razbivka po `vendorCodes`
        vendor_codes (list[str]): Artikuly prodavtsa
        errors (ModelsErrorTableListPublicRespV2ItemErrors): Oshibki. Razbivka po `vendorCodes`
    """

    batch_uuid: str
    subjects: ModelsErrorTableListPublicRespV2ItemSubjects
    brands: ModelsErrorTableListPublicRespV2ItemBrands
    vendor_codes: list[str]
    errors: ModelsErrorTableListPublicRespV2ItemErrors
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        batch_uuid = self.batch_uuid

        subjects = self.subjects.to_dict()

        brands = self.brands.to_dict()

        vendor_codes = self.vendor_codes

        errors = self.errors.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "batchUUID": batch_uuid,
                "subjects": subjects,
                "brands": brands,
                "vendorCodes": vendor_codes,
                "errors": errors,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.models_error_table_list_public_resp_v2_item_brands import (
            ModelsErrorTableListPublicRespV2ItemBrands,
        )
        from ..models.models_error_table_list_public_resp_v2_item_errors import (
            ModelsErrorTableListPublicRespV2ItemErrors,
        )
        from ..models.models_error_table_list_public_resp_v2_item_subjects import (
            ModelsErrorTableListPublicRespV2ItemSubjects,
        )

        d = dict(src_dict)
        batch_uuid = d.pop("batchUUID")

        subjects = ModelsErrorTableListPublicRespV2ItemSubjects.from_dict(
            d.pop("subjects")
        )

        brands = ModelsErrorTableListPublicRespV2ItemBrands.from_dict(d.pop("brands"))

        vendor_codes = cast(list[str], d.pop("vendorCodes"))

        errors = ModelsErrorTableListPublicRespV2ItemErrors.from_dict(d.pop("errors"))

        models_error_table_list_public_resp_v2_item = cls(
            batch_uuid=batch_uuid,
            subjects=subjects,
            brands=brands,
            vendor_codes=vendor_codes,
            errors=errors,
        )

        models_error_table_list_public_resp_v2_item.additional_properties = d
        return models_error_table_list_public_resp_v2_item

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
