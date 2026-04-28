""" Contains all the data models used in inputs/outputs """

from .advert_bids_kopecks import AdvertBidsKopecks
from .advert_n_ms_settings import AdvertNMsSettings
from .advert_settings import AdvertSettings
from .advert_settings_payment_type import AdvertSettingsPaymentType
from .advert_settings_placements import AdvertSettingsPlacements
from .advert_subject import AdvertSubject
from .daily_stats_1_item import DailyStats1Item
from .daily_stats_1_item_app_type_stats_item import DailyStats1ItemAppTypeStatsItem
from .daily_stats_2_item import DailyStats2Item
from .daily_stats_2_item_app_type_stats_item import DailyStats2ItemAppTypeStatsItem
from .field_400_response import Field400Response
from .full_stats_error import FullStatsError
from .full_stats_item import FullStatsItem
from .get_adv_v1_advert_response_200 import GetAdvV1AdvertResponse200
from .get_adv_v1_advert_response_200_extended import GetAdvV1AdvertResponse200Extended
from .get_adv_v1_advert_response_200_items_item import (
    GetAdvV1AdvertResponse200ItemsItem,
)
from .get_adv_v1_advert_response_200_items_item_show_hours_item import (
    GetAdvV1AdvertResponse200ItemsItemShowHoursItem,
)
from .get_adv_v1_adverts_response_200_item import GetAdvV1AdvertsResponse200Item
from .get_adv_v1_balance_response_200 import GetAdvV1BalanceResponse200
from .get_adv_v1_balance_response_200_cashbacks_item import (
    GetAdvV1BalanceResponse200CashbacksItem,
)
from .get_adv_v1_budget_response_200 import GetAdvV1BudgetResponse200
from .get_adv_v1_count_response_200 import GetAdvV1CountResponse200
from .get_adv_v1_count_response_200_adverts import GetAdvV1CountResponse200Adverts
from .get_adv_v1_payments_response_200_item import GetAdvV1PaymentsResponse200Item
from .get_adv_v1_promotion_count_response_200 import GetAdvV1PromotionCountResponse200
from .get_adv_v1_promotion_count_response_200_adverts_type_0_item import (
    GetAdvV1PromotionCountResponse200AdvertsType0Item,
)
from .get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item import (
    GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem,
)
from .get_adv_v1_supplier_subjects_response_200_type_0_item import (
    GetAdvV1SupplierSubjectsResponse200Type0Item,
)
from .get_adv_v1_upd_response_200_item import GetAdvV1UpdResponse200Item
from .get_adverts import GetAdverts
from .get_adverts_adverts_item import GetAdvertsAdvertsItem
from .get_adverts_adverts_item_status import GetAdvertsAdvertsItemStatus
from .get_api_advert_v2_adverts_payment_type import GetApiAdvertV2AdvertsPaymentType
from .patch_adv_v0_auction_nms_body import PatchAdvV0AuctionNmsBody
from .patch_adv_v0_auction_nms_body_nms_item import PatchAdvV0AuctionNmsBodyNmsItem
from .patch_adv_v0_auction_nms_body_nms_item_nms import (
    PatchAdvV0AuctionNmsBodyNmsItemNms,
)
from .patch_adv_v0_auction_nms_response_200 import PatchAdvV0AuctionNmsResponse200
from .patch_adv_v0_auction_nms_response_200_nms_item import (
    PatchAdvV0AuctionNmsResponse200NmsItem,
)
from .patch_adv_v0_auction_nms_response_200_nms_item_nms import (
    PatchAdvV0AuctionNmsResponse200NmsItemNms,
)
from .patch_api_advert_v1_bids_body import PatchApiAdvertV1BidsBody
from .patch_api_advert_v1_bids_body_bids_item import PatchApiAdvertV1BidsBodyBidsItem
from .patch_api_advert_v1_bids_body_bids_item_nm_bids_item import (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItem,
)
from .patch_api_advert_v1_bids_body_bids_item_nm_bids_item_placement import (
    PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement,
)
from .patch_api_advert_v1_bids_response_200 import PatchApiAdvertV1BidsResponse200
from .patch_api_advert_v1_bids_response_200_bids_item import (
    PatchApiAdvertV1BidsResponse200BidsItem,
)
from .patch_api_advert_v1_bids_response_200_bids_item_nm_bids_item import (
    PatchApiAdvertV1BidsResponse200BidsItemNmBidsItem,
)
from .placement_type import PlacementType
from .post_adv_v0_rename_body import PostAdvV0RenameBody
from .post_adv_v1_budget_deposit_body import PostAdvV1BudgetDepositBody
from .post_adv_v1_budget_deposit_response_400 import PostAdvV1BudgetDepositResponse400
from .post_adv_v2_seacat_save_ad_body import PostAdvV2SeacatSaveAdBody
from .post_adv_v2_seacat_save_ad_body_bid_type import PostAdvV2SeacatSaveAdBodyBidType
from .post_adv_v2_seacat_save_ad_body_payment_type import (
    PostAdvV2SeacatSaveAdBodyPaymentType,
)
from .post_adv_v2_seacat_save_ad_body_placement_types_item import (
    PostAdvV2SeacatSaveAdBodyPlacementTypesItem,
)
from .post_adv_v2_supplier_nms_response_200_item import (
    PostAdvV2SupplierNmsResponse200Item,
)
from .post_api_advert_v1_bids_min_body import PostApiAdvertV1BidsMinBody
from .post_api_advert_v1_bids_min_body_payment_type import (
    PostApiAdvertV1BidsMinBodyPaymentType,
)
from .post_api_advert_v1_bids_min_body_placement_types_item import (
    PostApiAdvertV1BidsMinBodyPlacementTypesItem,
)
from .post_api_advert_v1_bids_min_response_200 import PostApiAdvertV1BidsMinResponse200
from .post_api_advert_v1_bids_min_response_200_bids_item import (
    PostApiAdvertV1BidsMinResponse200BidsItem,
)
from .post_api_advert_v1_bids_min_response_200_bids_item_bids_item import (
    PostApiAdvertV1BidsMinResponse200BidsItemBidsItem,
)
from .promotions_goods_list import PromotionsGoodsList
from .put_adv_v0_auction_placements_body import PutAdvV0AuctionPlacementsBody
from .put_adv_v0_auction_placements_body_placements_item import (
    PutAdvV0AuctionPlacementsBodyPlacementsItem,
)
from .put_adv_v0_auction_placements_body_placements_item_placements import (
    PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
)
from .request_with_campaign_id import RequestWithCampaignID
from .request_with_date import RequestWithDate
from .request_with_interval import RequestWithInterval
from .request_with_interval_interval import RequestWithIntervalInterval
from .response_400 import Response400
from .response_adv_error_1 import ResponseAdvError1
from .response_with_return import ResponseWithReturn
from .standardized_batch_error import StandardizedBatchError
from .stat import Stat
from .stat_date import StatDate
from .stat_interval import StatInterval
from .stat_interval_interval import StatIntervalInterval
from .stats_1_item import Stats1Item
from .stats_2_item import Stats2Item
from .stats_blok_1 import StatsBlok1
from .stats_blok_2 import StatsBlok2
from .timestamps import Timestamps
from .v0_bid_recommendation_base import V0BidRecommendationBase
from .v0_bid_recommendation_base_bid_competitive_bid import (
    V0BidRecommendationBaseBidCompetitiveBid,
)
from .v0_bid_recommendation_base_bid_leaders_bid import (
    V0BidRecommendationBaseBidLeadersBid,
)
from .v0_bid_recommendation_base_bid_top_2 import V0BidRecommendationBaseBidTop2
from .v0_bid_recommendation_norm_query import V0BidRecommendationNormQuery
from .v0_bid_recommendation_reach_max import V0BidRecommendationReachMax
from .v0_bid_recommendation_reach_medium import V0BidRecommendationReachMedium
from .v0_bid_recommendation_reach_min import V0BidRecommendationReachMin
from .v0_bids_recommendations_response import V0BidsRecommendationsResponse
from .v0_get_norm_query_bids_item import V0GetNormQueryBidsItem
from .v0_get_norm_query_bids_request import V0GetNormQueryBidsRequest
from .v0_get_norm_query_bids_request_item import V0GetNormQueryBidsRequestItem
from .v0_get_norm_query_bids_response import V0GetNormQueryBidsResponse
from .v0_get_norm_query_list_request import V0GetNormQueryListRequest
from .v0_get_norm_query_list_request_item import V0GetNormQueryListRequestItem
from .v0_get_norm_query_list_response import V0GetNormQueryListResponse
from .v0_get_norm_query_list_response_item import V0GetNormQueryListResponseItem
from .v0_get_norm_query_list_response_item_norm_queries import (
    V0GetNormQueryListResponseItemNormQueries,
)
from .v0_get_norm_query_minus_request import V0GetNormQueryMinusRequest
from .v0_get_norm_query_minus_request_item import V0GetNormQueryMinusRequestItem
from .v0_get_norm_query_minus_response import V0GetNormQueryMinusResponse
from .v0_get_norm_query_minus_response_item import V0GetNormQueryMinusResponseItem
from .v0_get_norm_query_stats_item import V0GetNormQueryStatsItem
from .v0_get_norm_query_stats_item_stat import V0GetNormQueryStatsItemStat
from .v0_get_norm_query_stats_request import V0GetNormQueryStatsRequest
from .v0_get_norm_query_stats_request_items_item import (
    V0GetNormQueryStatsRequestItemsItem,
)
from .v0_get_norm_query_stats_response import V0GetNormQueryStatsResponse
from .v0_set_minus_norm_query_request import V0SetMinusNormQueryRequest
from .v0_set_norm_query_bids_request import V0SetNormQueryBidsRequest
from .v0_set_norm_query_bids_request_item import V0SetNormQueryBidsRequestItem
from .v1_get_norm_query_stats_request import V1GetNormQueryStatsRequest
from .v1_get_norm_query_stats_request_items_item import (
    V1GetNormQueryStatsRequestItemsItem,
)
from .v1_get_norm_query_stats_response import V1GetNormQueryStatsResponse
from .v1_get_norm_query_stats_response_item import V1GetNormQueryStatsResponseItem
from .v1_get_norm_query_stats_response_item_daily_stat import (
    V1GetNormQueryStatsResponseItemDailyStat,
)
from .v1_get_norm_query_stats_response_item_stat import (
    V1GetNormQueryStatsResponseItemStat,
)

__all__ = (
    "AdvertBidsKopecks",
    "AdvertNMsSettings",
    "AdvertSettings",
    "AdvertSettingsPaymentType",
    "AdvertSettingsPlacements",
    "AdvertSubject",
    "DailyStats1Item",
    "DailyStats1ItemAppTypeStatsItem",
    "DailyStats2Item",
    "DailyStats2ItemAppTypeStatsItem",
    "Field400Response",
    "FullStatsError",
    "FullStatsItem",
    "GetAdverts",
    "GetAdvertsAdvertsItem",
    "GetAdvertsAdvertsItemStatus",
    "GetAdvV1AdvertResponse200",
    "GetAdvV1AdvertResponse200Extended",
    "GetAdvV1AdvertResponse200ItemsItem",
    "GetAdvV1AdvertResponse200ItemsItemShowHoursItem",
    "GetAdvV1AdvertsResponse200Item",
    "GetAdvV1BalanceResponse200",
    "GetAdvV1BalanceResponse200CashbacksItem",
    "GetAdvV1BudgetResponse200",
    "GetAdvV1CountResponse200",
    "GetAdvV1CountResponse200Adverts",
    "GetAdvV1PaymentsResponse200Item",
    "GetAdvV1PromotionCountResponse200",
    "GetAdvV1PromotionCountResponse200AdvertsType0Item",
    "GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem",
    "GetAdvV1SupplierSubjectsResponse200Type0Item",
    "GetAdvV1UpdResponse200Item",
    "GetApiAdvertV2AdvertsPaymentType",
    "PatchAdvV0AuctionNmsBody",
    "PatchAdvV0AuctionNmsBodyNmsItem",
    "PatchAdvV0AuctionNmsBodyNmsItemNms",
    "PatchAdvV0AuctionNmsResponse200",
    "PatchAdvV0AuctionNmsResponse200NmsItem",
    "PatchAdvV0AuctionNmsResponse200NmsItemNms",
    "PatchApiAdvertV1BidsBody",
    "PatchApiAdvertV1BidsBodyBidsItem",
    "PatchApiAdvertV1BidsBodyBidsItemNmBidsItem",
    "PatchApiAdvertV1BidsBodyBidsItemNmBidsItemPlacement",
    "PatchApiAdvertV1BidsResponse200",
    "PatchApiAdvertV1BidsResponse200BidsItem",
    "PatchApiAdvertV1BidsResponse200BidsItemNmBidsItem",
    "PlacementType",
    "PostAdvV0RenameBody",
    "PostAdvV1BudgetDepositBody",
    "PostAdvV1BudgetDepositResponse400",
    "PostAdvV2SeacatSaveAdBody",
    "PostAdvV2SeacatSaveAdBodyBidType",
    "PostAdvV2SeacatSaveAdBodyPaymentType",
    "PostAdvV2SeacatSaveAdBodyPlacementTypesItem",
    "PostAdvV2SupplierNmsResponse200Item",
    "PostApiAdvertV1BidsMinBody",
    "PostApiAdvertV1BidsMinBodyPaymentType",
    "PostApiAdvertV1BidsMinBodyPlacementTypesItem",
    "PostApiAdvertV1BidsMinResponse200",
    "PostApiAdvertV1BidsMinResponse200BidsItem",
    "PostApiAdvertV1BidsMinResponse200BidsItemBidsItem",
    "PromotionsGoodsList",
    "PutAdvV0AuctionPlacementsBody",
    "PutAdvV0AuctionPlacementsBodyPlacementsItem",
    "PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements",
    "RequestWithCampaignID",
    "RequestWithDate",
    "RequestWithInterval",
    "RequestWithIntervalInterval",
    "Response400",
    "ResponseAdvError1",
    "ResponseWithReturn",
    "StandardizedBatchError",
    "Stat",
    "StatDate",
    "StatInterval",
    "StatIntervalInterval",
    "Stats1Item",
    "Stats2Item",
    "StatsBlok1",
    "StatsBlok2",
    "Timestamps",
    "V0BidRecommendationBase",
    "V0BidRecommendationBaseBidCompetitiveBid",
    "V0BidRecommendationBaseBidLeadersBid",
    "V0BidRecommendationBaseBidTop2",
    "V0BidRecommendationNormQuery",
    "V0BidRecommendationReachMax",
    "V0BidRecommendationReachMedium",
    "V0BidRecommendationReachMin",
    "V0BidsRecommendationsResponse",
    "V0GetNormQueryBidsItem",
    "V0GetNormQueryBidsRequest",
    "V0GetNormQueryBidsRequestItem",
    "V0GetNormQueryBidsResponse",
    "V0GetNormQueryListRequest",
    "V0GetNormQueryListRequestItem",
    "V0GetNormQueryListResponse",
    "V0GetNormQueryListResponseItem",
    "V0GetNormQueryListResponseItemNormQueries",
    "V0GetNormQueryMinusRequest",
    "V0GetNormQueryMinusRequestItem",
    "V0GetNormQueryMinusResponse",
    "V0GetNormQueryMinusResponseItem",
    "V0GetNormQueryStatsItem",
    "V0GetNormQueryStatsItemStat",
    "V0GetNormQueryStatsRequest",
    "V0GetNormQueryStatsRequestItemsItem",
    "V0GetNormQueryStatsResponse",
    "V0SetMinusNormQueryRequest",
    "V0SetNormQueryBidsRequest",
    "V0SetNormQueryBidsRequestItem",
    "V1GetNormQueryStatsRequest",
    "V1GetNormQueryStatsRequestItemsItem",
    "V1GetNormQueryStatsResponse",
    "V1GetNormQueryStatsResponseItem",
    "V1GetNormQueryStatsResponseItemDailyStat",
    "V1GetNormQueryStatsResponseItemStat",
)
