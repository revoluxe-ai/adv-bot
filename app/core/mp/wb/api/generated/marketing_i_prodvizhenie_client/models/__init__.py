""" Contains all the data models used in inputs/outputs """

from .auction_advert_bids import AuctionAdvertBids
from .auction_advert_n_ms_settings import AuctionAdvertNMsSettings
from .auction_advert_settings import AuctionAdvertSettings
from .auction_advert_settings_payment_type import AuctionAdvertSettingsPaymentType
from .auction_advert_settings_placements import AuctionAdvertSettingsPlacements
from .auction_advert_subject import AuctionAdvertSubject
from .booster_stats_item import BoosterStatsItem
from .daily_stats_1_item import DailyStats1Item
from .daily_stats_1_item_app_type_stats_item import DailyStats1ItemAppTypeStatsItem
from .daily_stats_2_item import DailyStats2Item
from .daily_stats_2_item_app_type_stats_item import DailyStats2ItemAppTypeStatsItem
from .days_item import DaysItem
from .days_item_apps_item import DaysItemAppsItem
from .days_item_apps_item_nm_item import DaysItemAppsItemNmItem
from .error_response import ErrorResponse
from .field_400_response import Field400Response
from .full_stats_error import FullStatsError
from .full_stats_item import FullStatsItem
from .get_adv_v0_auction_adverts_payment_type import GetAdvV0AuctionAdvertsPaymentType
from .get_adv_v0_auction_adverts_statuses import GetAdvV0AuctionAdvertsStatuses
from .get_adv_v0_config_response_200 import GetAdvV0ConfigResponse200
from .get_adv_v0_config_response_200_config_item import GetAdvV0ConfigResponse200ConfigItem
from .get_adv_v1_advert_response_200 import GetAdvV1AdvertResponse200
from .get_adv_v1_advert_response_200_extended import GetAdvV1AdvertResponse200Extended
from .get_adv_v1_advert_response_200_items_item import GetAdvV1AdvertResponse200ItemsItem
from .get_adv_v1_advert_response_200_items_item_show_hours_item import GetAdvV1AdvertResponse200ItemsItemShowHoursItem
from .get_adv_v1_adverts_response_200_item import GetAdvV1AdvertsResponse200Item
from .get_adv_v1_balance_response_200 import GetAdvV1BalanceResponse200
from .get_adv_v1_balance_response_200_cashbacks_item import GetAdvV1BalanceResponse200CashbacksItem
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
from .get_adv_v1_stat_words_response_200 import GetAdvV1StatWordsResponse200
from .get_adv_v1_stat_words_response_200_stat_item import GetAdvV1StatWordsResponse200StatItem
from .get_adv_v1_stat_words_response_200_words import GetAdvV1StatWordsResponse200Words
from .get_adv_v1_stat_words_response_200_words_keywords_item import GetAdvV1StatWordsResponse200WordsKeywordsItem
from .get_adv_v1_supplier_subjects_response_200_type_0_item import GetAdvV1SupplierSubjectsResponse200Type0Item
from .get_adv_v1_upd_response_200_item import GetAdvV1UpdResponse200Item
from .get_adv_v2_auto_stat_words_response_200 import GetAdvV2AutoStatWordsResponse200
from .get_adv_v2_auto_stat_words_response_200_clusters_item import GetAdvV2AutoStatWordsResponse200ClustersItem
from .get_auction_adverts import GetAuctionAdverts
from .get_auction_adverts_adverts_item import GetAuctionAdvertsAdvertsItem
from .get_auction_adverts_adverts_item_status import GetAuctionAdvertsAdvertsItemStatus
from .patch_adv_v0_auction_bids_body import PatchAdvV0AuctionBidsBody
from .patch_adv_v0_auction_bids_body_bids_item import PatchAdvV0AuctionBidsBodyBidsItem
from .patch_adv_v0_auction_bids_body_bids_item_nm_bids_item import PatchAdvV0AuctionBidsBodyBidsItemNmBidsItem
from .patch_adv_v0_auction_bids_body_bids_item_nm_bids_item_placement import (
    PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement,
)
from .patch_adv_v0_auction_bids_response_200 import PatchAdvV0AuctionBidsResponse200
from .patch_adv_v0_auction_bids_response_200_bids_item import PatchAdvV0AuctionBidsResponse200BidsItem
from .patch_adv_v0_auction_bids_response_200_bids_item_nm_bids_item import (
    PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem,
)
from .patch_adv_v0_auction_nms_body import PatchAdvV0AuctionNmsBody
from .patch_adv_v0_auction_nms_body_nms_item import PatchAdvV0AuctionNmsBodyNmsItem
from .patch_adv_v0_auction_nms_body_nms_item_nms import PatchAdvV0AuctionNmsBodyNmsItemNms
from .patch_adv_v0_auction_nms_response_200 import PatchAdvV0AuctionNmsResponse200
from .patch_adv_v0_auction_nms_response_200_nms_item import PatchAdvV0AuctionNmsResponse200NmsItem
from .patch_adv_v0_auction_nms_response_200_nms_item_nms import PatchAdvV0AuctionNmsResponse200NmsItemNms
from .patch_adv_v0_bids_body import PatchAdvV0BidsBody
from .patch_adv_v0_bids_response_400 import PatchAdvV0BidsResponse400
from .patch_adv_v0_bids_response_400_errors_item import PatchAdvV0BidsResponse400ErrorsItem
from .placement_type import PlacementType
from .post_adv_v0_bids_min_body import PostAdvV0BidsMinBody
from .post_adv_v0_bids_min_body_payment_type import PostAdvV0BidsMinBodyPaymentType
from .post_adv_v0_bids_min_body_placement_types_item import PostAdvV0BidsMinBodyPlacementTypesItem
from .post_adv_v0_bids_min_response_200 import PostAdvV0BidsMinResponse200
from .post_adv_v0_bids_min_response_200_bids_item import PostAdvV0BidsMinResponse200BidsItem
from .post_adv_v0_bids_min_response_200_bids_item_bids_item import PostAdvV0BidsMinResponse200BidsItemBidsItem
from .post_adv_v0_rename_body import PostAdvV0RenameBody
from .post_adv_v1_auto_set_excluded_body import PostAdvV1AutoSetExcludedBody
from .post_adv_v1_auto_updatenm_body import PostAdvV1AutoUpdatenmBody
from .post_adv_v1_budget_deposit_body import PostAdvV1BudgetDepositBody
from .post_adv_v1_budget_deposit_response_400 import PostAdvV1BudgetDepositResponse400
from .post_adv_v1_promotion_adverts_direction import PostAdvV1PromotionAdvertsDirection
from .post_adv_v1_promotion_adverts_order import PostAdvV1PromotionAdvertsOrder
from .post_adv_v1_promotion_adverts_status import PostAdvV1PromotionAdvertsStatus
from .post_adv_v1_promotion_adverts_type import PostAdvV1PromotionAdvertsType
from .post_adv_v1_search_set_excluded_body import PostAdvV1SearchSetExcludedBody
from .post_adv_v1_search_set_plus_body import PostAdvV1SearchSetPlusBody
from .post_adv_v1_search_set_plus_response_400 import PostAdvV1SearchSetPlusResponse400
from .post_adv_v2_seacat_save_ad_body import PostAdvV2SeacatSaveAdBody
from .post_adv_v2_seacat_save_ad_body_bid_type import PostAdvV2SeacatSaveAdBodyBidType
from .post_adv_v2_seacat_save_ad_body_placement_types_item import PostAdvV2SeacatSaveAdBodyPlacementTypesItem
from .post_adv_v2_supplier_nms_response_200_item import PostAdvV2SupplierNmsResponse200Item
from .promotions_goods_list import PromotionsGoodsList
from .put_adv_v0_auction_placements_body import PutAdvV0AuctionPlacementsBody
from .put_adv_v0_auction_placements_body_placements_item import PutAdvV0AuctionPlacementsBodyPlacementsItem
from .put_adv_v0_auction_placements_body_placements_item_placements import (
    PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
)
from .request_with_campaign_id import RequestWithCampaignID
from .request_with_date import RequestWithDate
from .request_with_interval import RequestWithInterval
from .request_with_interval_interval import RequestWithIntervalInterval
from .response_400 import Response400
from .response_adv_error_1 import ResponseAdvError1
from .response_info_advert import ResponseInfoAdvert
from .response_info_advert_params_item import ResponseInfoAdvertParamsItem
from .response_info_advert_params_item_intervals_item import ResponseInfoAdvertParamsItemIntervalsItem
from .response_info_advert_params_item_nms_item import ResponseInfoAdvertParamsItemNmsItem
from .response_info_advert_type_8 import ResponseInfoAdvertType8
from .response_info_advert_type_8_auto_params import ResponseInfoAdvertType8AutoParams
from .response_info_advert_type_8_auto_params_active import ResponseInfoAdvertType8AutoParamsActive
from .response_info_advert_type_8_auto_params_menus_item import ResponseInfoAdvertType8AutoParamsMenusItem
from .response_info_advert_type_8_auto_params_nm_cpm_item import ResponseInfoAdvertType8AutoParamsNmCPMItem
from .response_info_advert_type_8_auto_params_sets_item import ResponseInfoAdvertType8AutoParamsSetsItem
from .response_info_advert_type_8_auto_params_subject import ResponseInfoAdvertType8AutoParamsSubject
from .response_info_advert_type_9 import ResponseInfoAdvertType9
from .response_info_advert_type_9_auction_multibids_item import ResponseInfoAdvertType9AuctionMultibidsItem
from .response_info_advert_type_9_united_params_item import ResponseInfoAdvertType9UnitedParamsItem
from .response_info_advert_type_9_united_params_item_menus_item import ResponseInfoAdvertType9UnitedParamsItemMenusItem
from .response_info_advert_type_9_united_params_item_subject import ResponseInfoAdvertType9UnitedParamsItemSubject
from .response_with_date_type_0_item import ResponseWithDateType0Item
from .response_with_interval_item import ResponseWithIntervalItem
from .response_with_interval_item_interval import ResponseWithIntervalItemInterval
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
from .v0_advert_multi_bid_item import V0AdvertMultiBidItem
from .v0_advert_multibid import V0AdvertMultibid
from .v0_get_config_categories_response import V0GetConfigCategoriesResponse
from .v0_get_norm_query_bids_item import V0GetNormQueryBidsItem
from .v0_get_norm_query_bids_request import V0GetNormQueryBidsRequest
from .v0_get_norm_query_bids_request_item import V0GetNormQueryBidsRequestItem
from .v0_get_norm_query_bids_response import V0GetNormQueryBidsResponse
from .v0_get_norm_query_minus_request import V0GetNormQueryMinusRequest
from .v0_get_norm_query_minus_request_item import V0GetNormQueryMinusRequestItem
from .v0_get_norm_query_minus_response import V0GetNormQueryMinusResponse
from .v0_get_norm_query_minus_response_item import V0GetNormQueryMinusResponseItem
from .v0_get_norm_query_stats_item import V0GetNormQueryStatsItem
from .v0_get_norm_query_stats_item_stat import V0GetNormQueryStatsItemStat
from .v0_get_norm_query_stats_request import V0GetNormQueryStatsRequest
from .v0_get_norm_query_stats_request_items_item import V0GetNormQueryStatsRequestItemsItem
from .v0_get_norm_query_stats_response import V0GetNormQueryStatsResponse
from .v0_keywords_statistic import V0KeywordsStatistic
from .v0_keywords_statistics import V0KeywordsStatistics
from .v0_keywords_statistics_response import V0KeywordsStatisticsResponse
from .v0_set_minus_norm_query_request import V0SetMinusNormQueryRequest
from .v0_set_norm_query_bids_request import V0SetNormQueryBidsRequest
from .v0_set_norm_query_bids_request_item import V0SetNormQueryBidsRequestItem

__all__ = (
    "AuctionAdvertBids",
    "AuctionAdvertNMsSettings",
    "AuctionAdvertSettings",
    "AuctionAdvertSettingsPaymentType",
    "AuctionAdvertSettingsPlacements",
    "AuctionAdvertSubject",
    "BoosterStatsItem",
    "DailyStats1Item",
    "DailyStats1ItemAppTypeStatsItem",
    "DailyStats2Item",
    "DailyStats2ItemAppTypeStatsItem",
    "DaysItem",
    "DaysItemAppsItem",
    "DaysItemAppsItemNmItem",
    "ErrorResponse",
    "Field400Response",
    "FullStatsError",
    "FullStatsItem",
    "GetAdvV0AuctionAdvertsPaymentType",
    "GetAdvV0AuctionAdvertsStatuses",
    "GetAdvV0ConfigResponse200",
    "GetAdvV0ConfigResponse200ConfigItem",
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
    "GetAdvV1StatWordsResponse200",
    "GetAdvV1StatWordsResponse200StatItem",
    "GetAdvV1StatWordsResponse200Words",
    "GetAdvV1StatWordsResponse200WordsKeywordsItem",
    "GetAdvV1SupplierSubjectsResponse200Type0Item",
    "GetAdvV1UpdResponse200Item",
    "GetAdvV2AutoStatWordsResponse200",
    "GetAdvV2AutoStatWordsResponse200ClustersItem",
    "GetAuctionAdverts",
    "GetAuctionAdvertsAdvertsItem",
    "GetAuctionAdvertsAdvertsItemStatus",
    "PatchAdvV0AuctionBidsBody",
    "PatchAdvV0AuctionBidsBodyBidsItem",
    "PatchAdvV0AuctionBidsBodyBidsItemNmBidsItem",
    "PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement",
    "PatchAdvV0AuctionBidsResponse200",
    "PatchAdvV0AuctionBidsResponse200BidsItem",
    "PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem",
    "PatchAdvV0AuctionNmsBody",
    "PatchAdvV0AuctionNmsBodyNmsItem",
    "PatchAdvV0AuctionNmsBodyNmsItemNms",
    "PatchAdvV0AuctionNmsResponse200",
    "PatchAdvV0AuctionNmsResponse200NmsItem",
    "PatchAdvV0AuctionNmsResponse200NmsItemNms",
    "PatchAdvV0BidsBody",
    "PatchAdvV0BidsResponse400",
    "PatchAdvV0BidsResponse400ErrorsItem",
    "PlacementType",
    "PostAdvV0BidsMinBody",
    "PostAdvV0BidsMinBodyPaymentType",
    "PostAdvV0BidsMinBodyPlacementTypesItem",
    "PostAdvV0BidsMinResponse200",
    "PostAdvV0BidsMinResponse200BidsItem",
    "PostAdvV0BidsMinResponse200BidsItemBidsItem",
    "PostAdvV0RenameBody",
    "PostAdvV1AutoSetExcludedBody",
    "PostAdvV1AutoUpdatenmBody",
    "PostAdvV1BudgetDepositBody",
    "PostAdvV1BudgetDepositResponse400",
    "PostAdvV1PromotionAdvertsDirection",
    "PostAdvV1PromotionAdvertsOrder",
    "PostAdvV1PromotionAdvertsStatus",
    "PostAdvV1PromotionAdvertsType",
    "PostAdvV1SearchSetExcludedBody",
    "PostAdvV1SearchSetPlusBody",
    "PostAdvV1SearchSetPlusResponse400",
    "PostAdvV2SeacatSaveAdBody",
    "PostAdvV2SeacatSaveAdBodyBidType",
    "PostAdvV2SeacatSaveAdBodyPlacementTypesItem",
    "PostAdvV2SupplierNmsResponse200Item",
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
    "ResponseInfoAdvert",
    "ResponseInfoAdvertParamsItem",
    "ResponseInfoAdvertParamsItemIntervalsItem",
    "ResponseInfoAdvertParamsItemNmsItem",
    "ResponseInfoAdvertType8",
    "ResponseInfoAdvertType8AutoParams",
    "ResponseInfoAdvertType8AutoParamsActive",
    "ResponseInfoAdvertType8AutoParamsMenusItem",
    "ResponseInfoAdvertType8AutoParamsNmCPMItem",
    "ResponseInfoAdvertType8AutoParamsSetsItem",
    "ResponseInfoAdvertType8AutoParamsSubject",
    "ResponseInfoAdvertType9",
    "ResponseInfoAdvertType9AuctionMultibidsItem",
    "ResponseInfoAdvertType9UnitedParamsItem",
    "ResponseInfoAdvertType9UnitedParamsItemMenusItem",
    "ResponseInfoAdvertType9UnitedParamsItemSubject",
    "ResponseWithDateType0Item",
    "ResponseWithIntervalItem",
    "ResponseWithIntervalItemInterval",
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
    "V0AdvertMultibid",
    "V0AdvertMultiBidItem",
    "V0GetConfigCategoriesResponse",
    "V0GetNormQueryBidsItem",
    "V0GetNormQueryBidsRequest",
    "V0GetNormQueryBidsRequestItem",
    "V0GetNormQueryBidsResponse",
    "V0GetNormQueryMinusRequest",
    "V0GetNormQueryMinusRequestItem",
    "V0GetNormQueryMinusResponse",
    "V0GetNormQueryMinusResponseItem",
    "V0GetNormQueryStatsItem",
    "V0GetNormQueryStatsItemStat",
    "V0GetNormQueryStatsRequest",
    "V0GetNormQueryStatsRequestItemsItem",
    "V0GetNormQueryStatsResponse",
    "V0KeywordsStatistic",
    "V0KeywordsStatistics",
    "V0KeywordsStatisticsResponse",
    "V0SetMinusNormQueryRequest",
    "V0SetNormQueryBidsRequest",
    "V0SetNormQueryBidsRequestItem",
)
