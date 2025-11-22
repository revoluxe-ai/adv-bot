from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.level import Level
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.product_history_request_selected_period import ProductHistoryRequestSelectedPeriod


T = TypeVar("T", bound="ProductHistoryRequest")


@_attrs_define
class ProductHistoryRequest:
    """
    Attributes:
        selected_period (ProductHistoryRequestSelectedPeriod):
        nm_ids (List[int]): Artikuly WB, po kotorym nuzhno sostavit' otchet
        skip_deleted_nm (Union[Unset, bool]): Skryt' udalennye kartochki tovarov
        aggregation_level (Union[Unset, Level]): Tip agregatsii. Esli ne ukazano, to po umolchaniju ispol'zuetsja
            agregatsija po dnjam. <br> Dostupnye urovni agregatsii `day`, `week`
             Example: day.
    """

    selected_period: "ProductHistoryRequestSelectedPeriod"
    nm_ids: List[int]
    skip_deleted_nm: Union[Unset, bool] = UNSET
    aggregation_level: Union[Unset, Level] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        selected_period = self.selected_period.to_dict()

        nm_ids = self.nm_ids

        skip_deleted_nm = self.skip_deleted_nm

        aggregation_level: Union[Unset, str] = UNSET
        if not isinstance(self.aggregation_level, Unset):
            aggregation_level = self.aggregation_level.value

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "selectedPeriod": selected_period,
                "nmIds": nm_ids,
            }
        )
        if skip_deleted_nm is not UNSET:
            field_dict["skipDeletedNm"] = skip_deleted_nm
        if aggregation_level is not UNSET:
            field_dict["aggregationLevel"] = aggregation_level

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.product_history_request_selected_period import ProductHistoryRequestSelectedPeriod

        d = src_dict.copy()
        selected_period = ProductHistoryRequestSelectedPeriod.from_dict(d.pop("selectedPeriod"))

        nm_ids = cast(List[int], d.pop("nmIds"))

        skip_deleted_nm = d.pop("skipDeletedNm", UNSET)

        _aggregation_level = d.pop("aggregationLevel", UNSET)
        aggregation_level: Union[Unset, Level]
        if isinstance(_aggregation_level, Unset):
            aggregation_level = UNSET
        else:
            aggregation_level = Level(_aggregation_level)

        product_history_request = cls(
            selected_period=selected_period,
            nm_ids=nm_ids,
            skip_deleted_nm=skip_deleted_nm,
            aggregation_level=aggregation_level,
        )

        product_history_request.additional_properties = d
        return product_history_request

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
