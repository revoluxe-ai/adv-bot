from typing import Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.excise_report_request_countries_item import (
    ExciseReportRequestCountriesItem,
)
from ..types import UNSET, Unset

T = TypeVar("T", bound="ExciseReportRequest")


@_attrs_define
class ExciseReportRequest:
    """
    Example:
        {'countries': ['AM', 'RU']}

    Attributes:
        countries (Union[Unset, List[ExciseReportRequestCountriesItem]]): Country code in according with ISO 3166-2. Set
            the empty parameter to get data without filters by country
    """

    countries: Union[Unset, List[ExciseReportRequestCountriesItem]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        countries: Union[Unset, List[str]] = UNSET
        if not isinstance(self.countries, Unset):
            countries = []
            for countries_item_data in self.countries:
                countries_item = countries_item_data.value
                countries.append(countries_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if countries is not UNSET:
            field_dict["countries"] = countries

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        countries = []
        _countries = d.pop("countries", UNSET)
        for countries_item_data in _countries or []:
            countries_item = ExciseReportRequestCountriesItem(countries_item_data)

            countries.append(countries_item)

        excise_report_request = cls(
            countries=countries,
        )

        excise_report_request.additional_properties = d
        return excise_report_request

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
