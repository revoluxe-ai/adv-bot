import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.response_info_advert_type_9_auction_multibids_item import ResponseInfoAdvertType9AuctionMultibidsItem
    from ..models.response_info_advert_type_9_united_params_item import ResponseInfoAdvertType9UnitedParamsItem


T = TypeVar("T", bound="ResponseInfoAdvertType9")


@_attrs_define
class ResponseInfoAdvertType9:
    """
    Attributes:
        end_time (Union[Unset, datetime.datetime]): Data zavershenija kampanii
        create_time (Union[Unset, datetime.datetime]): Data sozdanija kampanii
        change_time (Union[Unset, datetime.datetime]): Data poslednego izmenenija kampanii
        start_time (Union[Unset, datetime.datetime]): Data poslednego zapuska kampanii
        search_pluse_state (Union[Unset, bool]): Aktivnost' fiksirovannyh fraz:
              - `false` — ne aktivny
              - `true` — aktivny
        name (Union[Unset, str]): Nazvanie kampanii
        united_params (Union[Unset, List['ResponseInfoAdvertType9UnitedParamsItem']]):
        daily_budget (Union[Unset, int]): Ne ispol'zuetsja
        advert_id (Union[Unset, int]): ID kampanii
        status (Union[Unset, int]): Status kampanii:
            - `-1` — udalena, protsess udalenija budet zavershen v techenie 10 minut
            - `4` — gotova k zapusku
            - `7` — zavershena
            - `8` — otmenena
            - `9` — aktivna
            - `11` — na pauze
        type (Union[Unset, int]): Tip kampanii:
              - `9` — Ruchnaja stavka
        payment_type (Union[Unset, str]): Model' oplaty:
            - `cpm` — za pokazy
        auction_multibids (Union[Unset, List['ResponseInfoAdvertType9AuctionMultibidsItem']]): Stavki artikulov WB
    """

    end_time: Union[Unset, datetime.datetime] = UNSET
    create_time: Union[Unset, datetime.datetime] = UNSET
    change_time: Union[Unset, datetime.datetime] = UNSET
    start_time: Union[Unset, datetime.datetime] = UNSET
    search_pluse_state: Union[Unset, bool] = UNSET
    name: Union[Unset, str] = UNSET
    united_params: Union[Unset, List["ResponseInfoAdvertType9UnitedParamsItem"]] = UNSET
    daily_budget: Union[Unset, int] = UNSET
    advert_id: Union[Unset, int] = UNSET
    status: Union[Unset, int] = UNSET
    type: Union[Unset, int] = UNSET
    payment_type: Union[Unset, str] = UNSET
    auction_multibids: Union[Unset, List["ResponseInfoAdvertType9AuctionMultibidsItem"]] = UNSET
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        end_time: Union[Unset, str] = UNSET
        if not isinstance(self.end_time, Unset):
            end_time = self.end_time.isoformat()

        create_time: Union[Unset, str] = UNSET
        if not isinstance(self.create_time, Unset):
            create_time = self.create_time.isoformat()

        change_time: Union[Unset, str] = UNSET
        if not isinstance(self.change_time, Unset):
            change_time = self.change_time.isoformat()

        start_time: Union[Unset, str] = UNSET
        if not isinstance(self.start_time, Unset):
            start_time = self.start_time.isoformat()

        search_pluse_state = self.search_pluse_state

        name = self.name

        united_params: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.united_params, Unset):
            united_params = []
            for united_params_item_data in self.united_params:
                united_params_item = united_params_item_data.to_dict()
                united_params.append(united_params_item)

        daily_budget = self.daily_budget

        advert_id = self.advert_id

        status = self.status

        type = self.type

        payment_type = self.payment_type

        auction_multibids: Union[Unset, List[Dict[str, Any]]] = UNSET
        if not isinstance(self.auction_multibids, Unset):
            auction_multibids = []
            for auction_multibids_item_data in self.auction_multibids:
                auction_multibids_item = auction_multibids_item_data.to_dict()
                auction_multibids.append(auction_multibids_item)

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if end_time is not UNSET:
            field_dict["endTime"] = end_time
        if create_time is not UNSET:
            field_dict["createTime"] = create_time
        if change_time is not UNSET:
            field_dict["changeTime"] = change_time
        if start_time is not UNSET:
            field_dict["startTime"] = start_time
        if search_pluse_state is not UNSET:
            field_dict["searchPluseState"] = search_pluse_state
        if name is not UNSET:
            field_dict["name"] = name
        if united_params is not UNSET:
            field_dict["unitedParams"] = united_params
        if daily_budget is not UNSET:
            field_dict["dailyBudget"] = daily_budget
        if advert_id is not UNSET:
            field_dict["advertId"] = advert_id
        if status is not UNSET:
            field_dict["status"] = status
        if type is not UNSET:
            field_dict["type"] = type
        if payment_type is not UNSET:
            field_dict["paymentType"] = payment_type
        if auction_multibids is not UNSET:
            field_dict["auction_multibids"] = auction_multibids

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.response_info_advert_type_9_auction_multibids_item import (
            ResponseInfoAdvertType9AuctionMultibidsItem,
        )
        from ..models.response_info_advert_type_9_united_params_item import ResponseInfoAdvertType9UnitedParamsItem

        d = src_dict.copy()
        _end_time = d.pop("endTime", UNSET)
        end_time: Union[Unset, datetime.datetime]
        if isinstance(_end_time, Unset):
            end_time = UNSET
        else:
            end_time = isoparse(_end_time)

        _create_time = d.pop("createTime", UNSET)
        create_time: Union[Unset, datetime.datetime]
        if isinstance(_create_time, Unset):
            create_time = UNSET
        else:
            create_time = isoparse(_create_time)

        _change_time = d.pop("changeTime", UNSET)
        change_time: Union[Unset, datetime.datetime]
        if isinstance(_change_time, Unset):
            change_time = UNSET
        else:
            change_time = isoparse(_change_time)

        _start_time = d.pop("startTime", UNSET)
        start_time: Union[Unset, datetime.datetime]
        if isinstance(_start_time, Unset):
            start_time = UNSET
        else:
            start_time = isoparse(_start_time)

        search_pluse_state = d.pop("searchPluseState", UNSET)

        name = d.pop("name", UNSET)

        united_params = []
        _united_params = d.pop("unitedParams", UNSET)
        for united_params_item_data in _united_params or []:
            united_params_item = ResponseInfoAdvertType9UnitedParamsItem.from_dict(united_params_item_data)

            united_params.append(united_params_item)

        daily_budget = d.pop("dailyBudget", UNSET)

        advert_id = d.pop("advertId", UNSET)

        status = d.pop("status", UNSET)

        type = d.pop("type", UNSET)

        payment_type = d.pop("paymentType", UNSET)

        auction_multibids = []
        _auction_multibids = d.pop("auction_multibids", UNSET)
        for auction_multibids_item_data in _auction_multibids or []:
            auction_multibids_item = ResponseInfoAdvertType9AuctionMultibidsItem.from_dict(auction_multibids_item_data)

            auction_multibids.append(auction_multibids_item)

        response_info_advert_type_9 = cls(
            end_time=end_time,
            create_time=create_time,
            change_time=change_time,
            start_time=start_time,
            search_pluse_state=search_pluse_state,
            name=name,
            united_params=united_params,
            daily_budget=daily_budget,
            advert_id=advert_id,
            status=status,
            type=type,
            payment_type=payment_type,
            auction_multibids=auction_multibids,
        )

        response_info_advert_type_9.additional_properties = d
        return response_info_advert_type_9

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
