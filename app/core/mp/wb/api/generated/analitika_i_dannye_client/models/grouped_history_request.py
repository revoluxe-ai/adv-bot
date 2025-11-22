from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.level import Level
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.grouped_history_request_selected_period import GroupedHistoryRequestSelectedPeriod


T = TypeVar("T", bound="GroupedHistoryRequest")


@_attrs_define
class GroupedHistoryRequest:
    """
    Attributes:
        selected_period (GroupedHistoryRequestSelectedPeriod):
        brand_names (Union[Unset, List[str]]): Spisok brendov dlja fil'tratsii Example: ['nike', 'adidas'].
        subject_ids (Union[Unset, List[int]]): Spisok ID predmetov dlja fil'tratsii Example: [64, 334].
        tag_ids (Union[Unset, List[int]]): Spisok ID jarlykov dlja fil'tratsii Example: [32, 53].
        skip_deleted_nm (Union[Unset, bool]): Skryt' udalennye kartochki tovarov
        aggregation_level (Union[Unset, Level]): Tip agregatsii. Esli ne ukazano, to po umolchaniju ispol'zuetsja
            agregatsija po dnjam. <br> Dostupnye urovni agregatsii `day`, `week`
             Example: day.
    """

    selected_period: "GroupedHistoryRequestSelectedPeriod"
    brand_names: Union[Unset, List[str]] = UNSET
    subject_ids: Union[Unset, List[int]] = UNSET
    tag_ids: Union[Unset, List[int]] = UNSET
    skip_deleted_nm: Union[Unset, bool] = UNSET
    aggregation_level: Union[Unset, Level] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        selected_period = self.selected_period.to_dict()

        brand_names: Union[Unset, List[str]] = UNSET
        if not isinstance(self.brand_names, Unset):
            brand_names = self.brand_names

        subject_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.subject_ids, Unset):
            subject_ids = self.subject_ids

        tag_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.tag_ids, Unset):
            tag_ids = self.tag_ids

        skip_deleted_nm = self.skip_deleted_nm

        aggregation_level: Union[Unset, str] = UNSET
        if not isinstance(self.aggregation_level, Unset):
            aggregation_level = self.aggregation_level.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "selectedPeriod": selected_period,
            }
        )
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if subject_ids is not UNSET:
            field_dict["subjectIds"] = subject_ids
        if tag_ids is not UNSET:
            field_dict["tagIds"] = tag_ids
        if skip_deleted_nm is not UNSET:
            field_dict["skipDeletedNm"] = skip_deleted_nm
        if aggregation_level is not UNSET:
            field_dict["aggregationLevel"] = aggregation_level

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.grouped_history_request_selected_period import GroupedHistoryRequestSelectedPeriod

        d = src_dict.copy()
        selected_period = GroupedHistoryRequestSelectedPeriod.from_dict(d.pop("selectedPeriod"))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        subject_ids = cast(List[int], d.pop("subjectIds", UNSET))

        tag_ids = cast(List[int], d.pop("tagIds", UNSET))

        skip_deleted_nm = d.pop("skipDeletedNm", UNSET)

        _aggregation_level = d.pop("aggregationLevel", UNSET)
        aggregation_level: Union[Unset, Level]
        if isinstance(_aggregation_level, Unset):
            aggregation_level = UNSET
        else:
            aggregation_level = Level(_aggregation_level)

        grouped_history_request = cls(
            selected_period=selected_period,
            brand_names=brand_names,
            subject_ids=subject_ids,
            tag_ids=tag_ids,
            skip_deleted_nm=skip_deleted_nm,
            aggregation_level=aggregation_level,
        )

        grouped_history_request.additional_properties = d
        return grouped_history_request

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
