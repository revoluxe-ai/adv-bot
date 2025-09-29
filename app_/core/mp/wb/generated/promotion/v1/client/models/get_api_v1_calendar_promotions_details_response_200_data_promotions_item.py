from collections.abc import Mapping
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    Union,
    cast,
)

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.get_api_v1_calendar_promotions_details_response_200_data_promotions_item_type import (
    GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType,
)
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.get_api_v1_calendar_promotions_details_response_200_data_promotions_item_ranging_item import (
        GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem,
    )


T = TypeVar("T", bound="GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItem")


@_attrs_define
class GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItem:
    """
    Attributes:
        id (Union[Unset, int]): ID aktsii Example: 123.
        name (Union[Unset, str]): Nazvanie aktsii Example: HITY GODA.
        description (Union[Unset, str]): Opisanie aktsii Example: V aktsii prinimajut uchastie samye populjarnye tovary
            2023 goda. Kartochki tovarov budut vydeleny plashkoj «HIT GODA», chtoby pokupateli zamechali eti tovary sredi
            drugih. Takzhe oni budut razmescheny pod bannerami na glavnoj stranitse i primut uchastie v PUSH-uvedomlenijah.
            S tsenami dlja vstuplenija v aktsiju vy mozhete oznakomit'sja nizhe..
        advantages (Union[Unset, list[str]]): Preimuschestva aktsii Example: ['Plashka', 'Banner', 'Top vydachi
            tovarov'].
        start_date_time (Union[Unset, str]): Nachalo aktsii Example: 2023-06-05T21:00:00Z.
        end_date_time (Union[Unset, str]): Konets aktsii Example: 2023-06-05T21:00:00Z.
        in_promo_action_leftovers (Union[Unset, int]): Kolichestvo tovarov s ostatkami, uchastvujuschih v aktsii
            Example: 45.
        in_promo_action_total (Union[Unset, int]): Obschee kolichestvo tovarov, uchastvujuschih v aktsii Example: 123.
        not_in_promo_action_leftovers (Union[Unset, int]): Kolichestvo tovarov s ostatkami, ne uchastvujuschih v aktsii
            Example: 3.
        not_in_promo_action_total (Union[Unset, int]): Obschee kolichestvo tovarov, ne uchastvujuschih v aktsii Example:
            10.
        participation_percentage (Union[Unset, int]): Uzhe uchastvujuschie v aktsii tovary, %. Rasschityvaetsja po
            tovaram v aktsii i s ostatkom Example: 10.
        type_ (Union[Unset, GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType]): Tip aktsii:
              - `regular` — aktsija
              - `auto` — avtoaktsija
             Example: auto.
        exception_products_count (Union[Unset, int]): Kolichestvo tovarov, iskljuchennyh iz avtoaktsii do ee starta.
            Tol'ko pri `"type": "auto"`.
            <br>V moment starta aktsii eti tovary avtomaticheski budut bez skidki
             Example: 10.
        ranging (Union[Unset, list['GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem']]):
            Ranzhirovanie (esli podkljucheno) Example: [{'condition': 'productsInPromotion', 'participationRate': 10,
            'boost': 7}, {'condition': 'calculateProducts', 'participationRate': 20, 'boost': 17}, {'condition':
            'allProducts', 'participationRate': 35, 'boost': 30}].
    """

    id: Union[Unset, int] = UNSET
    name: Union[Unset, str] = UNSET
    description: Union[Unset, str] = UNSET
    advantages: Union[Unset, list[str]] = UNSET
    start_date_time: Union[Unset, str] = UNSET
    end_date_time: Union[Unset, str] = UNSET
    in_promo_action_leftovers: Union[Unset, int] = UNSET
    in_promo_action_total: Union[Unset, int] = UNSET
    not_in_promo_action_leftovers: Union[Unset, int] = UNSET
    not_in_promo_action_total: Union[Unset, int] = UNSET
    participation_percentage: Union[Unset, int] = UNSET
    type_: Union[
        Unset, GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType
    ] = UNSET
    exception_products_count: Union[Unset, int] = UNSET
    ranging: Union[
        Unset,
        list[
            "GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem"
        ],
    ] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        description = self.description

        advantages: Union[Unset, list[str]] = UNSET
        if not isinstance(self.advantages, Unset):
            advantages = self.advantages

        start_date_time = self.start_date_time

        end_date_time = self.end_date_time

        in_promo_action_leftovers = self.in_promo_action_leftovers

        in_promo_action_total = self.in_promo_action_total

        not_in_promo_action_leftovers = self.not_in_promo_action_leftovers

        not_in_promo_action_total = self.not_in_promo_action_total

        participation_percentage = self.participation_percentage

        type_: Union[Unset, str] = UNSET
        if not isinstance(self.type_, Unset):
            type_ = self.type_.value

        exception_products_count = self.exception_products_count

        ranging: Union[Unset, list[dict[str, Any]]] = UNSET
        if not isinstance(self.ranging, Unset):
            ranging = []
            for ranging_item_data in self.ranging:
                ranging_item = ranging_item_data.to_dict()
                ranging.append(ranging_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if id is not UNSET:
            field_dict["id"] = id
        if name is not UNSET:
            field_dict["name"] = name
        if description is not UNSET:
            field_dict["description"] = description
        if advantages is not UNSET:
            field_dict["advantages"] = advantages
        if start_date_time is not UNSET:
            field_dict["startDateTime"] = start_date_time
        if end_date_time is not UNSET:
            field_dict["endDateTime"] = end_date_time
        if in_promo_action_leftovers is not UNSET:
            field_dict["inPromoActionLeftovers"] = in_promo_action_leftovers
        if in_promo_action_total is not UNSET:
            field_dict["inPromoActionTotal"] = in_promo_action_total
        if not_in_promo_action_leftovers is not UNSET:
            field_dict["notInPromoActionLeftovers"] = not_in_promo_action_leftovers
        if not_in_promo_action_total is not UNSET:
            field_dict["notInPromoActionTotal"] = not_in_promo_action_total
        if participation_percentage is not UNSET:
            field_dict["participationPercentage"] = participation_percentage
        if type_ is not UNSET:
            field_dict["type"] = type_
        if exception_products_count is not UNSET:
            field_dict["exceptionProductsCount"] = exception_products_count
        if ranging is not UNSET:
            field_dict["ranging"] = ranging

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.get_api_v1_calendar_promotions_details_response_200_data_promotions_item_ranging_item import (
            GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem,
        )

        d = dict(src_dict)
        id = d.pop("id", UNSET)

        name = d.pop("name", UNSET)

        description = d.pop("description", UNSET)

        advantages = cast(list[str], d.pop("advantages", UNSET))

        start_date_time = d.pop("startDateTime", UNSET)

        end_date_time = d.pop("endDateTime", UNSET)

        in_promo_action_leftovers = d.pop("inPromoActionLeftovers", UNSET)

        in_promo_action_total = d.pop("inPromoActionTotal", UNSET)

        not_in_promo_action_leftovers = d.pop("notInPromoActionLeftovers", UNSET)

        not_in_promo_action_total = d.pop("notInPromoActionTotal", UNSET)

        participation_percentage = d.pop("participationPercentage", UNSET)

        _type_ = d.pop("type", UNSET)
        type_: Union[
            Unset, GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType
        ]
        if isinstance(_type_, Unset):
            type_ = UNSET
        else:
            type_ = GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType(
                _type_
            )

        exception_products_count = d.pop("exceptionProductsCount", UNSET)

        ranging = []
        _ranging = d.pop("ranging", UNSET)
        for ranging_item_data in _ranging or []:
            ranging_item = GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem.from_dict(
                ranging_item_data
            )

            ranging.append(ranging_item)

        get_api_v1_calendar_promotions_details_response_200_data_promotions_item = cls(
            id=id,
            name=name,
            description=description,
            advantages=advantages,
            start_date_time=start_date_time,
            end_date_time=end_date_time,
            in_promo_action_leftovers=in_promo_action_leftovers,
            in_promo_action_total=in_promo_action_total,
            not_in_promo_action_leftovers=not_in_promo_action_leftovers,
            not_in_promo_action_total=not_in_promo_action_total,
            participation_percentage=participation_percentage,
            type_=type_,
            exception_products_count=exception_products_count,
            ranging=ranging,
        )

        get_api_v1_calendar_promotions_details_response_200_data_promotions_item.additional_properties = d
        return get_api_v1_calendar_promotions_details_response_200_data_promotions_item

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
