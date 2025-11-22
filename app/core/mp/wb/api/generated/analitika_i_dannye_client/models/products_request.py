from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.order_by import OrderBy
    from ..models.products_request_past_period import ProductsRequestPastPeriod
    from ..models.products_request_selected_period import ProductsRequestSelectedPeriod


T = TypeVar("T", bound="ProductsRequest")


@_attrs_define
class ProductsRequest:
    """
    Attributes:
        selected_period (ProductsRequestSelectedPeriod):
        past_period (Union[Unset, ProductsRequestPastPeriod]):
        nm_ids (Union[Unset, List[int]]): Artikuly WB, po kotorym nuzhno sostavit' otchet. Ostav'te pustym, chtoby
            poluchit' otchet obo vseh tovarah
             Example: [1234567].
        brand_names (Union[Unset, List[str]]): Spisok brendov dlja fil'tratsii Example: ['nike', 'adidas'].
        subject_ids (Union[Unset, List[int]]): Spisok ID predmetov dlja fil'tratsii Example: [64, 334].
        tag_ids (Union[Unset, List[int]]): Spisok ID jarlykov dlja fil'tratsii Example: [32, 53].
        skip_deleted_nm (Union[Unset, bool]): Skryt' udalennye kartochki tovarov
        order_by (Union[Unset, OrderBy]): Parametry sortirovki
        limit (Union[Unset, int]): Kolichestvo kartochek tovara v otvete Default: 50. Example: 50.
        offset (Union[Unset, int]): Skol'ko elementov propustit'. Naprimer, dlja znachenija `10` otvet nachnetsja s 11
            elementa Default: 0. Example: 10.
    """

    selected_period: "ProductsRequestSelectedPeriod"
    past_period: Union[Unset, "ProductsRequestPastPeriod"] = UNSET
    nm_ids: Union[Unset, List[int]] = UNSET
    brand_names: Union[Unset, List[str]] = UNSET
    subject_ids: Union[Unset, List[int]] = UNSET
    tag_ids: Union[Unset, List[int]] = UNSET
    skip_deleted_nm: Union[Unset, bool] = UNSET
    order_by: Union[Unset, "OrderBy"] = UNSET
    limit: Union[Unset, int] = 50
    offset: Union[Unset, int] = 0
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        selected_period = self.selected_period.to_dict()

        past_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.past_period, Unset):
            past_period = self.past_period.to_dict()

        nm_ids: Union[Unset, List[int]] = UNSET
        if not isinstance(self.nm_ids, Unset):
            nm_ids = self.nm_ids

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

        order_by: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.order_by, Unset):
            order_by = self.order_by.to_dict()

        limit = self.limit

        offset = self.offset

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "selectedPeriod": selected_period,
            }
        )
        if past_period is not UNSET:
            field_dict["pastPeriod"] = past_period
        if nm_ids is not UNSET:
            field_dict["nmIds"] = nm_ids
        if brand_names is not UNSET:
            field_dict["brandNames"] = brand_names
        if subject_ids is not UNSET:
            field_dict["subjectIds"] = subject_ids
        if tag_ids is not UNSET:
            field_dict["tagIds"] = tag_ids
        if skip_deleted_nm is not UNSET:
            field_dict["skipDeletedNm"] = skip_deleted_nm
        if order_by is not UNSET:
            field_dict["orderBy"] = order_by
        if limit is not UNSET:
            field_dict["limit"] = limit
        if offset is not UNSET:
            field_dict["offset"] = offset

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.order_by import OrderBy
        from ..models.products_request_past_period import ProductsRequestPastPeriod
        from ..models.products_request_selected_period import ProductsRequestSelectedPeriod

        d = src_dict.copy()
        selected_period = ProductsRequestSelectedPeriod.from_dict(d.pop("selectedPeriod"))

        _past_period = d.pop("pastPeriod", UNSET)
        past_period: Union[Unset, ProductsRequestPastPeriod]
        if isinstance(_past_period, Unset):
            past_period = UNSET
        else:
            past_period = ProductsRequestPastPeriod.from_dict(_past_period)

        nm_ids = cast(List[int], d.pop("nmIds", UNSET))

        brand_names = cast(List[str], d.pop("brandNames", UNSET))

        subject_ids = cast(List[int], d.pop("subjectIds", UNSET))

        tag_ids = cast(List[int], d.pop("tagIds", UNSET))

        skip_deleted_nm = d.pop("skipDeletedNm", UNSET)

        _order_by = d.pop("orderBy", UNSET)
        order_by: Union[Unset, OrderBy]
        if isinstance(_order_by, Unset):
            order_by = UNSET
        else:
            order_by = OrderBy.from_dict(_order_by)

        limit = d.pop("limit", UNSET)

        offset = d.pop("offset", UNSET)

        products_request = cls(
            selected_period=selected_period,
            past_period=past_period,
            nm_ids=nm_ids,
            brand_names=brand_names,
            subject_ids=subject_ids,
            tag_ids=tag_ids,
            skip_deleted_nm=skip_deleted_nm,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

        products_request.additional_properties = d
        return products_request

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
