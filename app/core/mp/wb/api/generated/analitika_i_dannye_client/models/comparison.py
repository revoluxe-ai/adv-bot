from typing import TYPE_CHECKING, Any, Dict, List, Type, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.comparison_conversions import ComparisonConversions
    from ..models.comparison_time_to_ready_dynamic import ComparisonTimeToReadyDynamic
    from ..models.comparison_wb_club_dynamic import ComparisonWbClubDynamic


T = TypeVar("T", bound="Comparison")


@_attrs_define
class Comparison:
    """
    Attributes:
        open_count_dynamic (int): Dinamika perehodov v kartochku tovara Example: 10.
        cart_count_dynamic (int): Dinamika dobavlenij v korzinu Example: 30.
        order_count_dynamic (int): Dinamika kolichestva zakazov Example: -100.
        order_sum_dynamic (int): Dinamika summy zakazov Example: -100.
        buyout_count_dynamic (int): Dinamika vykupov Example: -100.
        buyout_sum_dynamic (int): Dinamika summy vykupov Example: -100.
        cancel_count_dynamic (int): Dinamika otmen tovarov
        cancel_sum_dynamic (int): Dinamika summ otmen tovarov
        avg_orders_count_per_day_dynamic (int): Dinamika srednego kolichestva zakazov v den'
        avg_price_dynamic (int): Dinamika srednej tseny na tovary. Uchityvajutsja skidki dlja aktsij Example: -100.
        share_order_percent_dynamic (int): Dinamika doli v vyruchke Example: -80.
        add_to_wishlist_dynamic (int): Dinamika dobavlenij tovara v izbrannoe Example: 60.
        time_to_ready_dynamic (ComparisonTimeToReadyDynamic):
        localization_percent_dynamic (int): Dinamika lokal'nyh zakazov v ramkah odnogo regiona Example: 46.
        wb_club_dynamic (ComparisonWbClubDynamic):
        conversions (ComparisonConversions):
    """

    open_count_dynamic: int
    cart_count_dynamic: int
    order_count_dynamic: int
    order_sum_dynamic: int
    buyout_count_dynamic: int
    buyout_sum_dynamic: int
    cancel_count_dynamic: int
    cancel_sum_dynamic: int
    avg_orders_count_per_day_dynamic: int
    avg_price_dynamic: int
    share_order_percent_dynamic: int
    add_to_wishlist_dynamic: int
    time_to_ready_dynamic: "ComparisonTimeToReadyDynamic"
    localization_percent_dynamic: int
    wb_club_dynamic: "ComparisonWbClubDynamic"
    conversions: "ComparisonConversions"
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        open_count_dynamic = self.open_count_dynamic

        cart_count_dynamic = self.cart_count_dynamic

        order_count_dynamic = self.order_count_dynamic

        order_sum_dynamic = self.order_sum_dynamic

        buyout_count_dynamic = self.buyout_count_dynamic

        buyout_sum_dynamic = self.buyout_sum_dynamic

        cancel_count_dynamic = self.cancel_count_dynamic

        cancel_sum_dynamic = self.cancel_sum_dynamic

        avg_orders_count_per_day_dynamic = self.avg_orders_count_per_day_dynamic

        avg_price_dynamic = self.avg_price_dynamic

        share_order_percent_dynamic = self.share_order_percent_dynamic

        add_to_wishlist_dynamic = self.add_to_wishlist_dynamic

        time_to_ready_dynamic = self.time_to_ready_dynamic.to_dict()

        localization_percent_dynamic = self.localization_percent_dynamic

        wb_club_dynamic = self.wb_club_dynamic.to_dict()

        conversions = self.conversions.to_dict()

        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "openCountDynamic": open_count_dynamic,
                "cartCountDynamic": cart_count_dynamic,
                "orderCountDynamic": order_count_dynamic,
                "orderSumDynamic": order_sum_dynamic,
                "buyoutCountDynamic": buyout_count_dynamic,
                "buyoutSumDynamic": buyout_sum_dynamic,
                "cancelCountDynamic": cancel_count_dynamic,
                "cancelSumDynamic": cancel_sum_dynamic,
                "avgOrdersCountPerDayDynamic": avg_orders_count_per_day_dynamic,
                "avgPriceDynamic": avg_price_dynamic,
                "shareOrderPercentDynamic": share_order_percent_dynamic,
                "addToWishlistDynamic": add_to_wishlist_dynamic,
                "timeToReadyDynamic": time_to_ready_dynamic,
                "localizationPercentDynamic": localization_percent_dynamic,
                "wbClubDynamic": wb_club_dynamic,
                "conversions": conversions,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        from ..models.comparison_conversions import ComparisonConversions
        from ..models.comparison_time_to_ready_dynamic import ComparisonTimeToReadyDynamic
        from ..models.comparison_wb_club_dynamic import ComparisonWbClubDynamic

        d = src_dict.copy()
        open_count_dynamic = d.pop("openCountDynamic")

        cart_count_dynamic = d.pop("cartCountDynamic")

        order_count_dynamic = d.pop("orderCountDynamic")

        order_sum_dynamic = d.pop("orderSumDynamic")

        buyout_count_dynamic = d.pop("buyoutCountDynamic")

        buyout_sum_dynamic = d.pop("buyoutSumDynamic")

        cancel_count_dynamic = d.pop("cancelCountDynamic")

        cancel_sum_dynamic = d.pop("cancelSumDynamic")

        avg_orders_count_per_day_dynamic = d.pop("avgOrdersCountPerDayDynamic")

        avg_price_dynamic = d.pop("avgPriceDynamic")

        share_order_percent_dynamic = d.pop("shareOrderPercentDynamic")

        add_to_wishlist_dynamic = d.pop("addToWishlistDynamic")

        time_to_ready_dynamic = ComparisonTimeToReadyDynamic.from_dict(d.pop("timeToReadyDynamic"))

        localization_percent_dynamic = d.pop("localizationPercentDynamic")

        wb_club_dynamic = ComparisonWbClubDynamic.from_dict(d.pop("wbClubDynamic"))

        conversions = ComparisonConversions.from_dict(d.pop("conversions"))

        comparison = cls(
            open_count_dynamic=open_count_dynamic,
            cart_count_dynamic=cart_count_dynamic,
            order_count_dynamic=order_count_dynamic,
            order_sum_dynamic=order_sum_dynamic,
            buyout_count_dynamic=buyout_count_dynamic,
            buyout_sum_dynamic=buyout_sum_dynamic,
            cancel_count_dynamic=cancel_count_dynamic,
            cancel_sum_dynamic=cancel_sum_dynamic,
            avg_orders_count_per_day_dynamic=avg_orders_count_per_day_dynamic,
            avg_price_dynamic=avg_price_dynamic,
            share_order_percent_dynamic=share_order_percent_dynamic,
            add_to_wishlist_dynamic=add_to_wishlist_dynamic,
            time_to_ready_dynamic=time_to_ready_dynamic,
            localization_percent_dynamic=localization_percent_dynamic,
            wb_club_dynamic=wb_club_dynamic,
            conversions=conversions,
        )

        comparison.additional_properties = d
        return comparison

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
