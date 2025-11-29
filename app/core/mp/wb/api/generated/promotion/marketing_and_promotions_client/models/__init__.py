"""Contains all the data models used in inputs/outputs"""

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
from .delete_adv_v0_normquery_bids_response_401 import (
    DeleteAdvV0NormqueryBidsResponse401,
)
from .delete_adv_v0_normquery_bids_response_429 import (
    DeleteAdvV0NormqueryBidsResponse429,
)
from .error_response import ErrorResponse
from .field_400_response import Field400Response
from .full_stats_error import FullStatsError
from .full_stats_item import FullStatsItem
from .get_adv_v0_auction_adverts_payment_type import GetAdvV0AuctionAdvertsPaymentType
from .get_adv_v0_auction_adverts_response_401 import GetAdvV0AuctionAdvertsResponse401
from .get_adv_v0_auction_adverts_response_429 import GetAdvV0AuctionAdvertsResponse429
from .get_adv_v0_auction_adverts_statuses import GetAdvV0AuctionAdvertsStatuses
from .get_adv_v0_config_response_200 import GetAdvV0ConfigResponse200
from .get_adv_v0_config_response_200_config_item import (
    GetAdvV0ConfigResponse200ConfigItem,
)
from .get_adv_v0_config_response_401 import GetAdvV0ConfigResponse401
from .get_adv_v0_config_response_429 import GetAdvV0ConfigResponse429
from .get_adv_v0_delete_response_401 import GetAdvV0DeleteResponse401
from .get_adv_v0_delete_response_429 import GetAdvV0DeleteResponse429
from .get_adv_v0_pause_response_401 import GetAdvV0PauseResponse401
from .get_adv_v0_pause_response_429 import GetAdvV0PauseResponse429
from .get_adv_v0_start_response_401 import GetAdvV0StartResponse401
from .get_adv_v0_start_response_429 import GetAdvV0StartResponse429
from .get_adv_v0_stats_keywords_response_401 import GetAdvV0StatsKeywordsResponse401
from .get_adv_v0_stats_keywords_response_429 import GetAdvV0StatsKeywordsResponse429
from .get_adv_v0_stop_response_401 import GetAdvV0StopResponse401
from .get_adv_v0_stop_response_429 import GetAdvV0StopResponse429
from .get_adv_v1_advert_response_200 import GetAdvV1AdvertResponse200
from .get_adv_v1_advert_response_200_extended import GetAdvV1AdvertResponse200Extended
from .get_adv_v1_advert_response_200_items_item import (
    GetAdvV1AdvertResponse200ItemsItem,
)
from .get_adv_v1_advert_response_200_items_item_show_hours_item import (
    GetAdvV1AdvertResponse200ItemsItemShowHoursItem,
)
from .get_adv_v1_advert_response_401 import GetAdvV1AdvertResponse401
from .get_adv_v1_advert_response_429 import GetAdvV1AdvertResponse429
from .get_adv_v1_adverts_response_200_item import GetAdvV1AdvertsResponse200Item
from .get_adv_v1_adverts_response_401 import GetAdvV1AdvertsResponse401
from .get_adv_v1_adverts_response_429 import GetAdvV1AdvertsResponse429
from .get_adv_v1_auto_getnmtoadd_response_401 import GetAdvV1AutoGetnmtoaddResponse401
from .get_adv_v1_auto_getnmtoadd_response_429 import GetAdvV1AutoGetnmtoaddResponse429
from .get_adv_v1_balance_response_200 import GetAdvV1BalanceResponse200
from .get_adv_v1_balance_response_200_cashbacks_item import (
    GetAdvV1BalanceResponse200CashbacksItem,
)
from .get_adv_v1_balance_response_401 import GetAdvV1BalanceResponse401
from .get_adv_v1_balance_response_429 import GetAdvV1BalanceResponse429
from .get_adv_v1_budget_response_200 import GetAdvV1BudgetResponse200
from .get_adv_v1_budget_response_401 import GetAdvV1BudgetResponse401
from .get_adv_v1_budget_response_429 import GetAdvV1BudgetResponse429
from .get_adv_v1_count_response_200 import GetAdvV1CountResponse200
from .get_adv_v1_count_response_200_adverts import GetAdvV1CountResponse200Adverts
from .get_adv_v1_count_response_401 import GetAdvV1CountResponse401
from .get_adv_v1_count_response_429 import GetAdvV1CountResponse429
from .get_adv_v1_payments_response_200_item import GetAdvV1PaymentsResponse200Item
from .get_adv_v1_payments_response_401 import GetAdvV1PaymentsResponse401
from .get_adv_v1_payments_response_429 import GetAdvV1PaymentsResponse429
from .get_adv_v1_promotion_count_response_200 import GetAdvV1PromotionCountResponse200
from .get_adv_v1_promotion_count_response_200_adverts_type_0_item import (
    GetAdvV1PromotionCountResponse200AdvertsType0Item,
)
from .get_adv_v1_promotion_count_response_200_adverts_type_0_item_advert_list_item import (
    GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem,
)
from .get_adv_v1_promotion_count_response_401 import GetAdvV1PromotionCountResponse401
from .get_adv_v1_promotion_count_response_429 import GetAdvV1PromotionCountResponse429
from .get_adv_v1_search_set_plus_response_401 import GetAdvV1SearchSetPlusResponse401
from .get_adv_v1_search_set_plus_response_429 import GetAdvV1SearchSetPlusResponse429
from .get_adv_v1_stat_words_response_200 import GetAdvV1StatWordsResponse200
from .get_adv_v1_stat_words_response_200_stat_item import (
    GetAdvV1StatWordsResponse200StatItem,
)
from .get_adv_v1_stat_words_response_200_words import GetAdvV1StatWordsResponse200Words
from .get_adv_v1_stat_words_response_200_words_keywords_item import (
    GetAdvV1StatWordsResponse200WordsKeywordsItem,
)
from .get_adv_v1_stat_words_response_401 import GetAdvV1StatWordsResponse401
from .get_adv_v1_stat_words_response_429 import GetAdvV1StatWordsResponse429
from .get_adv_v1_supplier_subjects_response_200_type_0_item import (
    GetAdvV1SupplierSubjectsResponse200Type0Item,
)
from .get_adv_v1_supplier_subjects_response_401 import (
    GetAdvV1SupplierSubjectsResponse401,
)
from .get_adv_v1_supplier_subjects_response_429 import (
    GetAdvV1SupplierSubjectsResponse429,
)
from .get_adv_v1_upd_response_200_item import GetAdvV1UpdResponse200Item
from .get_adv_v1_upd_response_401 import GetAdvV1UpdResponse401
from .get_adv_v1_upd_response_429 import GetAdvV1UpdResponse429
from .get_adv_v2_auto_stat_words_response_200 import GetAdvV2AutoStatWordsResponse200
from .get_adv_v2_auto_stat_words_response_200_clusters_item import (
    GetAdvV2AutoStatWordsResponse200ClustersItem,
)
from .get_adv_v2_auto_stat_words_response_401 import GetAdvV2AutoStatWordsResponse401
from .get_adv_v2_auto_stat_words_response_429 import GetAdvV2AutoStatWordsResponse429
from .get_adv_v3_fullstats_response_401 import GetAdvV3FullstatsResponse401
from .get_adv_v3_fullstats_response_429 import GetAdvV3FullstatsResponse429
from .get_api_v1_calendar_promotions_details_response_200 import (
    GetApiV1CalendarPromotionsDetailsResponse200,
)
from .get_api_v1_calendar_promotions_details_response_200_data import (
    GetApiV1CalendarPromotionsDetailsResponse200Data,
)
from .get_api_v1_calendar_promotions_details_response_200_data_promotions_item import (
    GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItem,
)
from .get_api_v1_calendar_promotions_details_response_200_data_promotions_item_ranging_item import (
    GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem,
)
from .get_api_v1_calendar_promotions_details_response_200_data_promotions_item_type import (
    GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType,
)
from .get_api_v1_calendar_promotions_details_response_400 import (
    GetApiV1CalendarPromotionsDetailsResponse400,
)
from .get_api_v1_calendar_promotions_details_response_401 import (
    GetApiV1CalendarPromotionsDetailsResponse401,
)
from .get_api_v1_calendar_promotions_details_response_429 import (
    GetApiV1CalendarPromotionsDetailsResponse429,
)
from .get_api_v1_calendar_promotions_nomenclatures_response_200 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse200,
)
from .get_api_v1_calendar_promotions_nomenclatures_response_200_data import (
    GetApiV1CalendarPromotionsNomenclaturesResponse200Data,
)
from .get_api_v1_calendar_promotions_nomenclatures_response_400 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse400,
)
from .get_api_v1_calendar_promotions_nomenclatures_response_401 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse401,
)
from .get_api_v1_calendar_promotions_nomenclatures_response_422 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse422,
)
from .get_api_v1_calendar_promotions_nomenclatures_response_429 import (
    GetApiV1CalendarPromotionsNomenclaturesResponse429,
)
from .get_api_v1_calendar_promotions_response_200 import (
    GetApiV1CalendarPromotionsResponse200,
)
from .get_api_v1_calendar_promotions_response_200_data import (
    GetApiV1CalendarPromotionsResponse200Data,
)
from .get_api_v1_calendar_promotions_response_200_data_promotions_item import (
    GetApiV1CalendarPromotionsResponse200DataPromotionsItem,
)
from .get_api_v1_calendar_promotions_response_200_data_promotions_item_type import (
    GetApiV1CalendarPromotionsResponse200DataPromotionsItemType,
)
from .get_api_v1_calendar_promotions_response_400 import (
    GetApiV1CalendarPromotionsResponse400,
)
from .get_api_v1_calendar_promotions_response_401 import (
    GetApiV1CalendarPromotionsResponse401,
)
from .get_api_v1_calendar_promotions_response_429 import (
    GetApiV1CalendarPromotionsResponse429,
)
from .get_auction_adverts import GetAuctionAdverts
from .get_auction_adverts_adverts_item import GetAuctionAdvertsAdvertsItem
from .get_auction_adverts_adverts_item_status import GetAuctionAdvertsAdvertsItemStatus
from .patch_adv_v0_auction_bids_body import PatchAdvV0AuctionBidsBody
from .patch_adv_v0_auction_bids_body_bids_item import PatchAdvV0AuctionBidsBodyBidsItem
from .patch_adv_v0_auction_bids_body_bids_item_nm_bids_item import (
    PatchAdvV0AuctionBidsBodyBidsItemNmBidsItem,
)
from .patch_adv_v0_auction_bids_body_bids_item_nm_bids_item_placement import (
    PatchAdvV0AuctionBidsBodyBidsItemNmBidsItemPlacement,
)
from .patch_adv_v0_auction_bids_response_200 import PatchAdvV0AuctionBidsResponse200
from .patch_adv_v0_auction_bids_response_200_bids_item import (
    PatchAdvV0AuctionBidsResponse200BidsItem,
)
from .patch_adv_v0_auction_bids_response_200_bids_item_nm_bids_item import (
    PatchAdvV0AuctionBidsResponse200BidsItemNmBidsItem,
)
from .patch_adv_v0_auction_bids_response_401 import PatchAdvV0AuctionBidsResponse401
from .patch_adv_v0_auction_bids_response_429 import PatchAdvV0AuctionBidsResponse429
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
from .patch_adv_v0_auction_nms_response_401 import PatchAdvV0AuctionNmsResponse401
from .patch_adv_v0_auction_nms_response_429 import PatchAdvV0AuctionNmsResponse429
from .patch_adv_v0_bids_body import PatchAdvV0BidsBody
from .patch_adv_v0_bids_response_400 import PatchAdvV0BidsResponse400
from .patch_adv_v0_bids_response_400_errors_item import (
    PatchAdvV0BidsResponse400ErrorsItem,
)
from .patch_adv_v0_bids_response_401 import PatchAdvV0BidsResponse401
from .patch_adv_v0_bids_response_429 import PatchAdvV0BidsResponse429
from .placement_type import PlacementType
from .post_adv_v0_bids_min_body import PostAdvV0BidsMinBody
from .post_adv_v0_bids_min_body_payment_type import PostAdvV0BidsMinBodyPaymentType
from .post_adv_v0_bids_min_body_placement_types_item import (
    PostAdvV0BidsMinBodyPlacementTypesItem,
)
from .post_adv_v0_bids_min_response_200 import PostAdvV0BidsMinResponse200
from .post_adv_v0_bids_min_response_200_bids_item import (
    PostAdvV0BidsMinResponse200BidsItem,
)
from .post_adv_v0_bids_min_response_200_bids_item_bids_item import (
    PostAdvV0BidsMinResponse200BidsItemBidsItem,
)
from .post_adv_v0_bids_min_response_401 import PostAdvV0BidsMinResponse401
from .post_adv_v0_bids_min_response_429 import PostAdvV0BidsMinResponse429
from .post_adv_v0_normquery_bids_response_401 import PostAdvV0NormqueryBidsResponse401
from .post_adv_v0_normquery_bids_response_429 import PostAdvV0NormqueryBidsResponse429
from .post_adv_v0_normquery_get_bids_response_401 import (
    PostAdvV0NormqueryGetBidsResponse401,
)
from .post_adv_v0_normquery_get_bids_response_429 import (
    PostAdvV0NormqueryGetBidsResponse429,
)
from .post_adv_v0_normquery_get_minus_response_401 import (
    PostAdvV0NormqueryGetMinusResponse401,
)
from .post_adv_v0_normquery_get_minus_response_429 import (
    PostAdvV0NormqueryGetMinusResponse429,
)
from .post_adv_v0_normquery_set_minus_response_401 import (
    PostAdvV0NormquerySetMinusResponse401,
)
from .post_adv_v0_normquery_set_minus_response_429 import (
    PostAdvV0NormquerySetMinusResponse429,
)
from .post_adv_v0_normquery_stats_response_401 import PostAdvV0NormqueryStatsResponse401
from .post_adv_v0_normquery_stats_response_429 import PostAdvV0NormqueryStatsResponse429
from .post_adv_v0_rename_body import PostAdvV0RenameBody
from .post_adv_v0_rename_response_401 import PostAdvV0RenameResponse401
from .post_adv_v0_rename_response_429 import PostAdvV0RenameResponse429
from .post_adv_v1_auto_set_excluded_body import PostAdvV1AutoSetExcludedBody
from .post_adv_v1_auto_set_excluded_response_401 import (
    PostAdvV1AutoSetExcludedResponse401,
)
from .post_adv_v1_auto_set_excluded_response_429 import (
    PostAdvV1AutoSetExcludedResponse429,
)
from .post_adv_v1_auto_updatenm_body import PostAdvV1AutoUpdatenmBody
from .post_adv_v1_auto_updatenm_response_401 import PostAdvV1AutoUpdatenmResponse401
from .post_adv_v1_auto_updatenm_response_429 import PostAdvV1AutoUpdatenmResponse429
from .post_adv_v1_budget_deposit_body import PostAdvV1BudgetDepositBody
from .post_adv_v1_budget_deposit_response_400 import PostAdvV1BudgetDepositResponse400
from .post_adv_v1_budget_deposit_response_401 import PostAdvV1BudgetDepositResponse401
from .post_adv_v1_budget_deposit_response_429 import PostAdvV1BudgetDepositResponse429
from .post_adv_v1_promotion_adverts_direction import PostAdvV1PromotionAdvertsDirection
from .post_adv_v1_promotion_adverts_order import PostAdvV1PromotionAdvertsOrder
from .post_adv_v1_promotion_adverts_response_401 import (
    PostAdvV1PromotionAdvertsResponse401,
)
from .post_adv_v1_promotion_adverts_response_429 import (
    PostAdvV1PromotionAdvertsResponse429,
)
from .post_adv_v1_promotion_adverts_status import PostAdvV1PromotionAdvertsStatus
from .post_adv_v1_promotion_adverts_type import PostAdvV1PromotionAdvertsType
from .post_adv_v1_search_set_excluded_body import PostAdvV1SearchSetExcludedBody
from .post_adv_v1_search_set_excluded_response_401 import (
    PostAdvV1SearchSetExcludedResponse401,
)
from .post_adv_v1_search_set_excluded_response_429 import (
    PostAdvV1SearchSetExcludedResponse429,
)
from .post_adv_v1_search_set_plus_body import PostAdvV1SearchSetPlusBody
from .post_adv_v1_search_set_plus_response_400 import PostAdvV1SearchSetPlusResponse400
from .post_adv_v1_search_set_plus_response_401 import PostAdvV1SearchSetPlusResponse401
from .post_adv_v1_search_set_plus_response_429 import PostAdvV1SearchSetPlusResponse429
from .post_adv_v1_stats_response_401 import PostAdvV1StatsResponse401
from .post_adv_v1_stats_response_429 import PostAdvV1StatsResponse429
from .post_adv_v2_fullstats_response_401 import PostAdvV2FullstatsResponse401
from .post_adv_v2_fullstats_response_429 import PostAdvV2FullstatsResponse429
from .post_adv_v2_seacat_save_ad_body import PostAdvV2SeacatSaveAdBody
from .post_adv_v2_seacat_save_ad_body_bid_type import PostAdvV2SeacatSaveAdBodyBidType
from .post_adv_v2_seacat_save_ad_body_placement_types_item import (
    PostAdvV2SeacatSaveAdBodyPlacementTypesItem,
)
from .post_adv_v2_seacat_save_ad_response_401 import PostAdvV2SeacatSaveAdResponse401
from .post_adv_v2_seacat_save_ad_response_429 import PostAdvV2SeacatSaveAdResponse429
from .post_adv_v2_supplier_nms_response_200_item import (
    PostAdvV2SupplierNmsResponse200Item,
)
from .post_adv_v2_supplier_nms_response_401 import PostAdvV2SupplierNmsResponse401
from .post_adv_v2_supplier_nms_response_429 import PostAdvV2SupplierNmsResponse429
from .post_api_v1_calendar_promotions_upload_body import (
    PostApiV1CalendarPromotionsUploadBody,
)
from .post_api_v1_calendar_promotions_upload_body_data import (
    PostApiV1CalendarPromotionsUploadBodyData,
)
from .post_api_v1_calendar_promotions_upload_response_200 import (
    PostApiV1CalendarPromotionsUploadResponse200,
)
from .post_api_v1_calendar_promotions_upload_response_200_data import (
    PostApiV1CalendarPromotionsUploadResponse200Data,
)
from .post_api_v1_calendar_promotions_upload_response_400 import (
    PostApiV1CalendarPromotionsUploadResponse400,
)
from .post_api_v1_calendar_promotions_upload_response_401 import (
    PostApiV1CalendarPromotionsUploadResponse401,
)
from .post_api_v1_calendar_promotions_upload_response_422 import (
    PostApiV1CalendarPromotionsUploadResponse422,
)
from .post_api_v1_calendar_promotions_upload_response_429 import (
    PostApiV1CalendarPromotionsUploadResponse429,
)
from .promotions_goods_list import PromotionsGoodsList
from .put_adv_v0_auction_placements_body import PutAdvV0AuctionPlacementsBody
from .put_adv_v0_auction_placements_body_placements_item import (
    PutAdvV0AuctionPlacementsBodyPlacementsItem,
)
from .put_adv_v0_auction_placements_body_placements_item_placements import (
    PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements,
)
from .put_adv_v0_auction_placements_response_401 import (
    PutAdvV0AuctionPlacementsResponse401,
)
from .put_adv_v0_auction_placements_response_429 import (
    PutAdvV0AuctionPlacementsResponse429,
)
from .request_with_campaign_id import RequestWithCampaignID
from .request_with_date import RequestWithDate
from .request_with_interval import RequestWithInterval
from .request_with_interval_interval import RequestWithIntervalInterval
from .response_400 import Response400
from .response_adv_error_1 import ResponseAdvError1
from .response_info_advert_type_8 import ResponseInfoAdvertType8
from .response_info_advert_type_8_auto_params import ResponseInfoAdvertType8AutoParams
from .response_info_advert_type_8_auto_params_active import (
    ResponseInfoAdvertType8AutoParamsActive,
)
from .response_info_advert_type_8_auto_params_menus_item import (
    ResponseInfoAdvertType8AutoParamsMenusItem,
)
from .response_info_advert_type_8_auto_params_nm_cpm_item import (
    ResponseInfoAdvertType8AutoParamsNmCPMItem,
)
from .response_info_advert_type_8_auto_params_sets_item import (
    ResponseInfoAdvertType8AutoParamsSetsItem,
)
from .response_info_advert_type_8_auto_params_subject import (
    ResponseInfoAdvertType8AutoParamsSubject,
)
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
from .v0_get_norm_query_stats_request_items_item import (
    V0GetNormQueryStatsRequestItemsItem,
)
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
    "DeleteAdvV0NormqueryBidsResponse401",
    "DeleteAdvV0NormqueryBidsResponse429",
    "ErrorResponse",
    "Field400Response",
    "FullStatsError",
    "FullStatsItem",
    "GetAdvV0AuctionAdvertsPaymentType",
    "GetAdvV0AuctionAdvertsResponse401",
    "GetAdvV0AuctionAdvertsResponse429",
    "GetAdvV0AuctionAdvertsStatuses",
    "GetAdvV0ConfigResponse200",
    "GetAdvV0ConfigResponse200ConfigItem",
    "GetAdvV0ConfigResponse401",
    "GetAdvV0ConfigResponse429",
    "GetAdvV0DeleteResponse401",
    "GetAdvV0DeleteResponse429",
    "GetAdvV0PauseResponse401",
    "GetAdvV0PauseResponse429",
    "GetAdvV0StartResponse401",
    "GetAdvV0StartResponse429",
    "GetAdvV0StatsKeywordsResponse401",
    "GetAdvV0StatsKeywordsResponse429",
    "GetAdvV0StopResponse401",
    "GetAdvV0StopResponse429",
    "GetAdvV1AdvertResponse200",
    "GetAdvV1AdvertResponse200Extended",
    "GetAdvV1AdvertResponse200ItemsItem",
    "GetAdvV1AdvertResponse200ItemsItemShowHoursItem",
    "GetAdvV1AdvertResponse401",
    "GetAdvV1AdvertResponse429",
    "GetAdvV1AdvertsResponse200Item",
    "GetAdvV1AdvertsResponse401",
    "GetAdvV1AdvertsResponse429",
    "GetAdvV1AutoGetnmtoaddResponse401",
    "GetAdvV1AutoGetnmtoaddResponse429",
    "GetAdvV1BalanceResponse200",
    "GetAdvV1BalanceResponse200CashbacksItem",
    "GetAdvV1BalanceResponse401",
    "GetAdvV1BalanceResponse429",
    "GetAdvV1BudgetResponse200",
    "GetAdvV1BudgetResponse401",
    "GetAdvV1BudgetResponse429",
    "GetAdvV1CountResponse200",
    "GetAdvV1CountResponse200Adverts",
    "GetAdvV1CountResponse401",
    "GetAdvV1CountResponse429",
    "GetAdvV1PaymentsResponse200Item",
    "GetAdvV1PaymentsResponse401",
    "GetAdvV1PaymentsResponse429",
    "GetAdvV1PromotionCountResponse200",
    "GetAdvV1PromotionCountResponse200AdvertsType0Item",
    "GetAdvV1PromotionCountResponse200AdvertsType0ItemAdvertListItem",
    "GetAdvV1PromotionCountResponse401",
    "GetAdvV1PromotionCountResponse429",
    "GetAdvV1SearchSetPlusResponse401",
    "GetAdvV1SearchSetPlusResponse429",
    "GetAdvV1StatWordsResponse200",
    "GetAdvV1StatWordsResponse200StatItem",
    "GetAdvV1StatWordsResponse200Words",
    "GetAdvV1StatWordsResponse200WordsKeywordsItem",
    "GetAdvV1StatWordsResponse401",
    "GetAdvV1StatWordsResponse429",
    "GetAdvV1SupplierSubjectsResponse200Type0Item",
    "GetAdvV1SupplierSubjectsResponse401",
    "GetAdvV1SupplierSubjectsResponse429",
    "GetAdvV1UpdResponse200Item",
    "GetAdvV1UpdResponse401",
    "GetAdvV1UpdResponse429",
    "GetAdvV2AutoStatWordsResponse200",
    "GetAdvV2AutoStatWordsResponse200ClustersItem",
    "GetAdvV2AutoStatWordsResponse401",
    "GetAdvV2AutoStatWordsResponse429",
    "GetAdvV3FullstatsResponse401",
    "GetAdvV3FullstatsResponse429",
    "GetApiV1CalendarPromotionsDetailsResponse200",
    "GetApiV1CalendarPromotionsDetailsResponse200Data",
    "GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItem",
    "GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemRangingItem",
    "GetApiV1CalendarPromotionsDetailsResponse200DataPromotionsItemType",
    "GetApiV1CalendarPromotionsDetailsResponse400",
    "GetApiV1CalendarPromotionsDetailsResponse401",
    "GetApiV1CalendarPromotionsDetailsResponse429",
    "GetApiV1CalendarPromotionsNomenclaturesResponse200",
    "GetApiV1CalendarPromotionsNomenclaturesResponse200Data",
    "GetApiV1CalendarPromotionsNomenclaturesResponse400",
    "GetApiV1CalendarPromotionsNomenclaturesResponse401",
    "GetApiV1CalendarPromotionsNomenclaturesResponse422",
    "GetApiV1CalendarPromotionsNomenclaturesResponse429",
    "GetApiV1CalendarPromotionsResponse200",
    "GetApiV1CalendarPromotionsResponse200Data",
    "GetApiV1CalendarPromotionsResponse200DataPromotionsItem",
    "GetApiV1CalendarPromotionsResponse200DataPromotionsItemType",
    "GetApiV1CalendarPromotionsResponse400",
    "GetApiV1CalendarPromotionsResponse401",
    "GetApiV1CalendarPromotionsResponse429",
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
    "PatchAdvV0AuctionBidsResponse401",
    "PatchAdvV0AuctionBidsResponse429",
    "PatchAdvV0AuctionNmsBody",
    "PatchAdvV0AuctionNmsBodyNmsItem",
    "PatchAdvV0AuctionNmsBodyNmsItemNms",
    "PatchAdvV0AuctionNmsResponse200",
    "PatchAdvV0AuctionNmsResponse200NmsItem",
    "PatchAdvV0AuctionNmsResponse200NmsItemNms",
    "PatchAdvV0AuctionNmsResponse401",
    "PatchAdvV0AuctionNmsResponse429",
    "PatchAdvV0BidsBody",
    "PatchAdvV0BidsResponse400",
    "PatchAdvV0BidsResponse400ErrorsItem",
    "PatchAdvV0BidsResponse401",
    "PatchAdvV0BidsResponse429",
    "PlacementType",
    "PostAdvV0BidsMinBody",
    "PostAdvV0BidsMinBodyPaymentType",
    "PostAdvV0BidsMinBodyPlacementTypesItem",
    "PostAdvV0BidsMinResponse200",
    "PostAdvV0BidsMinResponse200BidsItem",
    "PostAdvV0BidsMinResponse200BidsItemBidsItem",
    "PostAdvV0BidsMinResponse401",
    "PostAdvV0BidsMinResponse429",
    "PostAdvV0NormqueryBidsResponse401",
    "PostAdvV0NormqueryBidsResponse429",
    "PostAdvV0NormqueryGetBidsResponse401",
    "PostAdvV0NormqueryGetBidsResponse429",
    "PostAdvV0NormqueryGetMinusResponse401",
    "PostAdvV0NormqueryGetMinusResponse429",
    "PostAdvV0NormquerySetMinusResponse401",
    "PostAdvV0NormquerySetMinusResponse429",
    "PostAdvV0NormqueryStatsResponse401",
    "PostAdvV0NormqueryStatsResponse429",
    "PostAdvV0RenameBody",
    "PostAdvV0RenameResponse401",
    "PostAdvV0RenameResponse429",
    "PostAdvV1AutoSetExcludedBody",
    "PostAdvV1AutoSetExcludedResponse401",
    "PostAdvV1AutoSetExcludedResponse429",
    "PostAdvV1AutoUpdatenmBody",
    "PostAdvV1AutoUpdatenmResponse401",
    "PostAdvV1AutoUpdatenmResponse429",
    "PostAdvV1BudgetDepositBody",
    "PostAdvV1BudgetDepositResponse400",
    "PostAdvV1BudgetDepositResponse401",
    "PostAdvV1BudgetDepositResponse429",
    "PostAdvV1PromotionAdvertsDirection",
    "PostAdvV1PromotionAdvertsOrder",
    "PostAdvV1PromotionAdvertsResponse401",
    "PostAdvV1PromotionAdvertsResponse429",
    "PostAdvV1PromotionAdvertsStatus",
    "PostAdvV1PromotionAdvertsType",
    "PostAdvV1SearchSetExcludedBody",
    "PostAdvV1SearchSetExcludedResponse401",
    "PostAdvV1SearchSetExcludedResponse429",
    "PostAdvV1SearchSetPlusBody",
    "PostAdvV1SearchSetPlusResponse400",
    "PostAdvV1SearchSetPlusResponse401",
    "PostAdvV1SearchSetPlusResponse429",
    "PostAdvV1StatsResponse401",
    "PostAdvV1StatsResponse429",
    "PostAdvV2FullstatsResponse401",
    "PostAdvV2FullstatsResponse429",
    "PostAdvV2SeacatSaveAdBody",
    "PostAdvV2SeacatSaveAdBodyBidType",
    "PostAdvV2SeacatSaveAdBodyPlacementTypesItem",
    "PostAdvV2SeacatSaveAdResponse401",
    "PostAdvV2SeacatSaveAdResponse429",
    "PostAdvV2SupplierNmsResponse200Item",
    "PostAdvV2SupplierNmsResponse401",
    "PostAdvV2SupplierNmsResponse429",
    "PostApiV1CalendarPromotionsUploadBody",
    "PostApiV1CalendarPromotionsUploadBodyData",
    "PostApiV1CalendarPromotionsUploadResponse200",
    "PostApiV1CalendarPromotionsUploadResponse200Data",
    "PostApiV1CalendarPromotionsUploadResponse400",
    "PostApiV1CalendarPromotionsUploadResponse401",
    "PostApiV1CalendarPromotionsUploadResponse422",
    "PostApiV1CalendarPromotionsUploadResponse429",
    "PromotionsGoodsList",
    "PutAdvV0AuctionPlacementsBody",
    "PutAdvV0AuctionPlacementsBodyPlacementsItem",
    "PutAdvV0AuctionPlacementsBodyPlacementsItemPlacements",
    "PutAdvV0AuctionPlacementsResponse401",
    "PutAdvV0AuctionPlacementsResponse429",
    "RequestWithCampaignID",
    "RequestWithDate",
    "RequestWithInterval",
    "RequestWithIntervalInterval",
    "Response400",
    "ResponseAdvError1",
    "ResponseInfoAdvertType8",
    "ResponseInfoAdvertType8AutoParams",
    "ResponseInfoAdvertType8AutoParamsActive",
    "ResponseInfoAdvertType8AutoParamsMenusItem",
    "ResponseInfoAdvertType8AutoParamsNmCPMItem",
    "ResponseInfoAdvertType8AutoParamsSetsItem",
    "ResponseInfoAdvertType8AutoParamsSubject",
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
