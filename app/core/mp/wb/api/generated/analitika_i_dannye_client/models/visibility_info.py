from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.visibility_info_by_day_item import VisibilityInfoByDayItem
    from ..models.visibility_info_by_month_item import VisibilityInfoByMonthItem
    from ..models.visibility_info_by_week_item import VisibilityInfoByWeekItem
    from ..models.visibility_info_open_card import VisibilityInfoOpenCard
    from ..models.visibility_info_visibility import VisibilityInfoVisibility


T = TypeVar("T", bound="VisibilityInfo")


@_attrs_define
class VisibilityInfo:
    """Vidimost' kartochek i perehody v kartochki. Po dnjam, nedeljam, mesjatsam

    Attributes:
        visibility (VisibilityInfoVisibility): Vidimost' — protsent verojatnosti, chto pol'zovatel' uvidit kartochku
            tovara. Zavisit ot srednej pozitsii
        open_card (VisibilityInfoOpenCard): Kolichestvo perehodov v kartochku tovara iz poiska
        by_day (Union[Unset, List['VisibilityInfoByDayItem']]): Dannye dlja otrisovki grafika v lichnom kabinete po
            vidimosti i perehodam v kartochki po dnjam
        by_week (Union[Unset, List['VisibilityInfoByWeekItem']]): Dannye dlja otrisovki grafika v lichnom kabinete po
            vidimosti i perehodam v kartochki po nedeljam
        by_month (Union[Unset, List['VisibilityInfoByMonthItem']]): Dannye dlja otrisovki grafika v lichnom kabinete po
            vidimosti i perehodam v kartochki po mesjatsam
    """

    visibility: "VisibilityInfoVisibility"
    open_card: "VisibilityInfoOpenCard"
    by_day: Union[Unset, List["VisibilityInfoByDayItem"]] = UNSET
    by_week: Union[Unset, List["VisibilityInfoByWeekItem"]] = UNSET
    by_month: Union[Unset, List["VisibilityInfoByMonthItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        visibility = self.visibility.to_dict()

        open_card = self.open_card.to_dict()

        by_day: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.by_day, Unset):
            by_day = []
            for by_day_item_data in self.by_day:
                by_day_item = by_day_item_data.to_dict()
                by_day.append(by_day_item)

        by_week: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.by_week, Unset):
            by_week = []
            for by_week_item_data in self.by_week:
                by_week_item = by_week_item_data.to_dict()
                by_week.append(by_week_item)

        by_month: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.by_month, Unset):
            by_month = []
            for by_month_item_data in self.by_month:
                by_month_item = by_month_item_data.to_dict()
                by_month.append(by_month_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "visibility": visibility,
                "openCard": open_card,
            }
        )
        if by_day is not UNSET:
            field_dict["byDay"] = by_day
        if by_week is not UNSET:
            field_dict["byWeek"] = by_week
        if by_month is not UNSET:
            field_dict["byMonth"] = by_month

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.visibility_info_by_day_item import VisibilityInfoByDayItem
        from ..models.visibility_info_by_month_item import VisibilityInfoByMonthItem
        from ..models.visibility_info_by_week_item import VisibilityInfoByWeekItem
        from ..models.visibility_info_open_card import VisibilityInfoOpenCard
        from ..models.visibility_info_visibility import VisibilityInfoVisibility

        d = src_dict.copy()
        visibility = VisibilityInfoVisibility.from_dict(d.pop("visibility"))

        open_card = VisibilityInfoOpenCard.from_dict(d.pop("openCard"))

        by_day = []
        _by_day = d.pop("byDay", UNSET)
        for by_day_item_data in _by_day or []:
            by_day_item = VisibilityInfoByDayItem.from_dict(by_day_item_data)

            by_day.append(by_day_item)

        by_week = []
        _by_week = d.pop("byWeek", UNSET)
        for by_week_item_data in _by_week or []:
            by_week_item = VisibilityInfoByWeekItem.from_dict(by_week_item_data)

            by_week.append(by_week_item)

        by_month = []
        _by_month = d.pop("byMonth", UNSET)
        for by_month_item_data in _by_month or []:
            by_month_item = VisibilityInfoByMonthItem.from_dict(by_month_item_data)

            by_month.append(by_month_item)

        visibility_info = cls(
            visibility=visibility,
            open_card=open_card,
            by_day=by_day,
            by_week=by_week,
            by_month=by_month,
        )

        visibility_info.additional_properties = d
        return visibility_info

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
