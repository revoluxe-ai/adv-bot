from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_info_advert_type_8_auto_params_active import (
        ResponseInfoAdvertType8AutoParamsActive,
    )
    from ..models.response_info_advert_type_8_auto_params_menus_item import (
        ResponseInfoAdvertType8AutoParamsMenusItem,
    )
    from ..models.response_info_advert_type_8_auto_params_nm_cpm_item import (
        ResponseInfoAdvertType8AutoParamsNmCPMItem,
    )
    from ..models.response_info_advert_type_8_auto_params_sets_item import (
        ResponseInfoAdvertType8AutoParamsSetsItem,
    )
    from ..models.response_info_advert_type_8_auto_params_subject import (
        ResponseInfoAdvertType8AutoParamsSubject,
    )


T = TypeVar("T", bound="ResponseInfoAdvertType8AutoParams")


@_attrs_define
class ResponseInfoAdvertType8AutoParams:
    """
    Attributes:
        subject (ResponseInfoAdvertType8AutoParamsSubject | Unset): Prodvigaemyj predmet
        sets (list[ResponseInfoAdvertType8AutoParamsSetsItem] | Unset): Vnutrennjaja (sistemnaja) suschnost' (pol +
            predmet)
        menus (list[ResponseInfoAdvertType8AutoParamsMenusItem] | Unset):
        active (ResponseInfoAdvertType8AutoParamsActive | Unset): Mesta razmeschenija
        nm_cpm (list[ResponseInfoAdvertType8AutoParamsNmCPMItem] | Unset): Stavki kartochek tovarov
        nms (list[int] | Unset): Artikuly WB
        cpm (int | Unset): Stavka, ukazannaja pri sozdanii kampanii.<br> Pole aktual'no tol'ko dlja kampanij, sozdannyh
            cherez API.
    """

    subject: ResponseInfoAdvertType8AutoParamsSubject | Unset = UNSET
    sets: list[ResponseInfoAdvertType8AutoParamsSetsItem] | Unset = UNSET
    menus: list[ResponseInfoAdvertType8AutoParamsMenusItem] | Unset = UNSET
    active: ResponseInfoAdvertType8AutoParamsActive | Unset = UNSET
    nm_cpm: list[ResponseInfoAdvertType8AutoParamsNmCPMItem] | Unset = UNSET
    nms: list[int] | Unset = UNSET
    cpm: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        subject: dict[str, Any] | Unset = UNSET
        if not isinstance(self.subject, Unset):
            subject = self.subject.to_dict()

        sets: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.sets, Unset):
            sets = []
            for sets_item_data in self.sets:
                sets_item = sets_item_data.to_dict()
                sets.append(sets_item)

        menus: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.menus, Unset):
            menus = []
            for menus_item_data in self.menus:
                menus_item = menus_item_data.to_dict()
                menus.append(menus_item)

        active: dict[str, Any] | Unset = UNSET
        if not isinstance(self.active, Unset):
            active = self.active.to_dict()

        nm_cpm: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.nm_cpm, Unset):
            nm_cpm = []
            for nm_cpm_item_data in self.nm_cpm:
                nm_cpm_item = nm_cpm_item_data.to_dict()
                nm_cpm.append(nm_cpm_item)

        nms: list[int] | Unset = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        cpm = self.cpm

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if subject is not UNSET:
            field_dict["subject"] = subject
        if sets is not UNSET:
            field_dict["sets"] = sets
        if menus is not UNSET:
            field_dict["menus"] = menus
        if active is not UNSET:
            field_dict["active"] = active
        if nm_cpm is not UNSET:
            field_dict["nmCPM"] = nm_cpm
        if nms is not UNSET:
            field_dict["nms"] = nms
        if cpm is not UNSET:
            field_dict["cpm"] = cpm

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.response_info_advert_type_8_auto_params_active import (
            ResponseInfoAdvertType8AutoParamsActive,
        )
        from ..models.response_info_advert_type_8_auto_params_menus_item import (
            ResponseInfoAdvertType8AutoParamsMenusItem,
        )
        from ..models.response_info_advert_type_8_auto_params_nm_cpm_item import (
            ResponseInfoAdvertType8AutoParamsNmCPMItem,
        )
        from ..models.response_info_advert_type_8_auto_params_sets_item import (
            ResponseInfoAdvertType8AutoParamsSetsItem,
        )
        from ..models.response_info_advert_type_8_auto_params_subject import (
            ResponseInfoAdvertType8AutoParamsSubject,
        )

        d = dict(src_dict)
        _subject = d.pop("subject", UNSET)
        subject: ResponseInfoAdvertType8AutoParamsSubject | Unset
        if isinstance(_subject, Unset):
            subject = UNSET
        else:
            subject = ResponseInfoAdvertType8AutoParamsSubject.from_dict(_subject)

        _sets = d.pop("sets", UNSET)
        sets: list[ResponseInfoAdvertType8AutoParamsSetsItem] | Unset = UNSET
        if _sets is not UNSET:
            sets = []
            for sets_item_data in _sets:
                sets_item = ResponseInfoAdvertType8AutoParamsSetsItem.from_dict(
                    sets_item_data
                )

                sets.append(sets_item)

        _menus = d.pop("menus", UNSET)
        menus: list[ResponseInfoAdvertType8AutoParamsMenusItem] | Unset = UNSET
        if _menus is not UNSET:
            menus = []
            for menus_item_data in _menus:
                menus_item = ResponseInfoAdvertType8AutoParamsMenusItem.from_dict(
                    menus_item_data
                )

                menus.append(menus_item)

        _active = d.pop("active", UNSET)
        active: ResponseInfoAdvertType8AutoParamsActive | Unset
        if isinstance(_active, Unset):
            active = UNSET
        else:
            active = ResponseInfoAdvertType8AutoParamsActive.from_dict(_active)

        _nm_cpm = d.pop("nmCPM", UNSET)
        nm_cpm: list[ResponseInfoAdvertType8AutoParamsNmCPMItem] | Unset = UNSET
        if _nm_cpm is not UNSET:
            nm_cpm = []
            for nm_cpm_item_data in _nm_cpm:
                nm_cpm_item = ResponseInfoAdvertType8AutoParamsNmCPMItem.from_dict(
                    nm_cpm_item_data
                )

                nm_cpm.append(nm_cpm_item)

        nms = cast(list[int], d.pop("nms", UNSET))

        cpm = d.pop("cpm", UNSET)

        response_info_advert_type_8_auto_params = cls(
            subject=subject,
            sets=sets,
            menus=menus,
            active=active,
            nm_cpm=nm_cpm,
            nms=nms,
            cpm=cpm,
        )

        response_info_advert_type_8_auto_params.additional_properties = d
        return response_info_advert_type_8_auto_params

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
