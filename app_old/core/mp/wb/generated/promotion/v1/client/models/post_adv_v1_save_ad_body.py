from collections.abc import Mapping
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PostAdvV1SaveAdBody")


@_attrs_define
class PostAdvV1SaveAdBody:
    """
    Attributes:
        type_ (Union[Unset, int]): <dl>
            <dt>Tip kampanii s edinoj stavkoj:</dt>
            <dd><code>8</code>
            </dl>
             Example: 8.
        name (Union[Unset, str]): Nazvanie kampanii (max. 128 simvolov) Example: Parashjuty.
        subject_id (Union[Unset, int]): ID predmeta, dlja kotorogo sozdaetsja kampanija.<br>
            Suschestvujuschie u prodavtsa ID mozhno poluchit' metodom iz razdela "Kontent / Prosmotr" — "Spisok NM", pole
            otveta — `subjectID`.
             Example: 270.
        sum_ (Union[Unset, int]): Summa popolnenija Example: 500.
        btype (Union[Unset, int]): <dl>
            <dt>Tip spisanija:</dt>
            <dd><code>0</code> — Schet</dd>
            <dd><code>1</code> — Balans</dd>
            <dd><code>3</code> — Bonusy</dd>
            </dl>
             Example: 1.
        on_pause (Union[Unset, bool]): <dl>
            <dt>Posle sozdanija kampanija:</dt>
            <dd>
              <dl>
                <dt><code>true</code> — budet na pauze.</dt>
                <dd>Zapusk kampanii budet dostupen cherez 3 minuty posle sozdanija kampanii.</dd>
              </dl>
            </dd>
            <dd><code>false</code> — budet srazu zapuschena</dd>
            </dl>
             Example: True.
        nms (Union[Unset, list[int]]): Massiv artikulov WB. <br>
            Maksimum 100 artikulov.
        cpm (Union[Unset, int]): Stavka. <br>
            Esli budet ukazana stavka men'she dopustimogo razmera, to avtomaticheski ustanovitsja stavka minimal'no
            dopustimogo razmera.
    """

    type_: Union[Unset, int] = UNSET
    name: Union[Unset, str] = UNSET
    subject_id: Union[Unset, int] = UNSET
    sum_: Union[Unset, int] = UNSET
    btype: Union[Unset, int] = UNSET
    on_pause: Union[Unset, bool] = UNSET
    nms: Union[Unset, list[int]] = UNSET
    cpm: Union[Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        type_ = self.type_

        name = self.name

        subject_id = self.subject_id

        sum_ = self.sum_

        btype = self.btype

        on_pause = self.on_pause

        nms: Union[Unset, list[int]] = UNSET
        if not isinstance(self.nms, Unset):
            nms = self.nms

        cpm = self.cpm

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if type_ is not UNSET:
            field_dict["type"] = type_
        if name is not UNSET:
            field_dict["name"] = name
        if subject_id is not UNSET:
            field_dict["subjectId"] = subject_id
        if sum_ is not UNSET:
            field_dict["sum"] = sum_
        if btype is not UNSET:
            field_dict["btype"] = btype
        if on_pause is not UNSET:
            field_dict["on_pause"] = on_pause
        if nms is not UNSET:
            field_dict["nms"] = nms
        if cpm is not UNSET:
            field_dict["cpm"] = cpm

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        type_ = d.pop("type", UNSET)

        name = d.pop("name", UNSET)

        subject_id = d.pop("subjectId", UNSET)

        sum_ = d.pop("sum", UNSET)

        btype = d.pop("btype", UNSET)

        on_pause = d.pop("on_pause", UNSET)

        nms = cast(list[int], d.pop("nms", UNSET))

        cpm = d.pop("cpm", UNSET)

        post_adv_v1_save_ad_body = cls(
            type_=type_,
            name=name,
            subject_id=subject_id,
            sum_=sum_,
            btype=btype,
            on_pause=on_pause,
            nms=nms,
            cpm=cpm,
        )

        post_adv_v1_save_ad_body.additional_properties = d
        return post_adv_v1_save_ad_body

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
