from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.product_search_texts_request_top_order_by import ProductSearchTextsRequestTopOrderBy
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.order_by_gr_te import OrderByGrTe
    from ..models.past_period import PastPeriod
    from ..models.period import Period


T = TypeVar("T", bound="ProductSearchTextsRequest")


@_attrs_define
class ProductSearchTextsRequest:
    """Parametry dlja zaprosa po rejtingu poiskovyh zaprosov:
    - `currentPeriod` — tekuschij period
    - `pastPeriod` — predyduschij period dlja sravnenija

      Attributes:
          current_period (Period): Tekuschij period
          nm_ids (List[int]): Spisok artikulov WB Example: [162579635, 166699779].
          top_order_by (ProductSearchTextsRequestTopOrderBy): Fil'tratsija po poiskovym zaprosam, po kotorym bol'she
              vsego:
                - `openCard` — pereshli v kartochku
                - `addToCart` — dobavili v korzinu
                - `openToCart` — konversija v korzinu
                - `orders` — zakazali tovarov
                - `cartToOrder` — konversija v zakaz
               Example: openToCart.
          order_by (OrderByGrTe): Parametry sortirovki
          limit (int):
          past_period (Union[Unset, PastPeriod]): Proshlyj period dlja sravnenija. Kolichestvo dnej — men'she ili ravno
              `currentPeriod`
          include_substituted_sk_us (Union[Unset, bool]): Pokazat' dannye po prjamym zaprosam s [podmennym
              artikulom](https://seller.wildberries.ru/help-center/article/A-524) Default: True. Example: True.
          include_search_texts (Union[Unset, bool]): Pokazat' dannye po poiskovym zaprosam bez ucheta podmennogo artikula
              Default: True.
    """

    current_period: "Period"
    nm_ids: List[int]
    top_order_by: ProductSearchTextsRequestTopOrderBy
    order_by: "OrderByGrTe"
    limit: int
    past_period: Union[Unset, "PastPeriod"] = UNSET
    include_substituted_sk_us: Union[Unset, bool] = True
    include_search_texts: Union[Unset, bool] = True
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        current_period = self.current_period.to_dict()

        nm_ids = self.nm_ids

        top_order_by = self.top_order_by.value

        order_by = self.order_by.to_dict()

        limit: int
        limit = self.limit

        past_period: Union[Unset, Dict[str, Any]] = UNSET
        if not isinstance(self.past_period, Unset):
            past_period = self.past_period.to_dict()

        include_substituted_sk_us = self.include_substituted_sk_us

        include_search_texts = self.include_search_texts

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "currentPeriod": current_period,
                "nmIds": nm_ids,
                "topOrderBy": top_order_by,
                "orderBy": order_by,
                "limit": limit,
            }
        )
        if past_period is not UNSET:
            field_dict["pastPeriod"] = past_period
        if include_substituted_sk_us is not UNSET:
            field_dict["includeSubstitutedSKUs"] = include_substituted_sk_us
        if include_search_texts is not UNSET:
            field_dict["includeSearchTexts"] = include_search_texts

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.order_by_gr_te import OrderByGrTe
        from ..models.past_period import PastPeriod
        from ..models.period import Period

        d = src_dict.copy()
        current_period = Period.from_dict(d.pop("currentPeriod"))

        nm_ids = cast(List[int], d.pop("nmIds"))

        top_order_by = ProductSearchTextsRequestTopOrderBy(d.pop("topOrderBy"))

        order_by = OrderByGrTe.from_dict(d.pop("orderBy"))

        def _parse_limit(data: object) -> int:
            return cast(int, data)

        limit = _parse_limit(d.pop("limit"))

        _past_period = d.pop("pastPeriod", UNSET)
        past_period: Union[Unset, PastPeriod]
        if isinstance(_past_period, Unset):
            past_period = UNSET
        else:
            past_period = PastPeriod.from_dict(_past_period)

        include_substituted_sk_us = d.pop("includeSubstitutedSKUs", UNSET)

        include_search_texts = d.pop("includeSearchTexts", UNSET)

        product_search_texts_request = cls(
            current_period=current_period,
            nm_ids=nm_ids,
            top_order_by=top_order_by,
            order_by=order_by,
            limit=limit,
            past_period=past_period,
            include_substituted_sk_us=include_substituted_sk_us,
            include_search_texts=include_search_texts,
        )

        product_search_texts_request.additional_properties = d
        return product_search_texts_request

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
