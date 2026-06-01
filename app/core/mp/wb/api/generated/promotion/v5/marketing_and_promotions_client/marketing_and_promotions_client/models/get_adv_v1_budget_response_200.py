from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="GetAdvV1BudgetResponse200")


@_attrs_define
class GetAdvV1BudgetResponse200:
    """
    Attributes:
        cash (Union[Unset, int]): The field is not used. The value is always equal to 0.
        netting (Union[Unset, int]): The field is not used. The value is always equal to 0.
        total (Union[Unset, int]): Campaign budget, ₽
    """

    cash: Union[Unset, int] = UNSET
    netting: Union[Unset, int] = UNSET
    total: Union[Unset, int] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        cash = self.cash

        netting = self.netting

        total = self.total

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cash is not UNSET:
            field_dict["cash"] = cash
        if netting is not UNSET:
            field_dict["netting"] = netting
        if total is not UNSET:
            field_dict["total"] = total

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        cash = d.pop("cash", UNSET)

        netting = d.pop("netting", UNSET)

        total = d.pop("total", UNSET)

        get_adv_v1_budget_response_200 = cls(
            cash=cash,
            netting=netting,
            total=total,
        )

        get_adv_v1_budget_response_200.additional_properties = d
        return get_adv_v1_budget_response_200

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
