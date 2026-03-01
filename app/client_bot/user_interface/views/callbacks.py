from aiogram.filters.callback_data import CallbackData

from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.shared.domains.wb.enums import (
    AdvType,
)


class ChoiceAdvPaginator(CallbackData, prefix="choice_adv_paginator"):
    wb_user_cabinet_original_id: int
    page: int
    reset_filter: bool = False


class Action:
    new = "new"
    select = "select"
    buy = "buy"


class BudgetForCreatingAdv(CallbackData, prefix="budget"):
    type: str


class Shop(CallbackData, prefix="shop"):
    action: str
    wb_user_cabinet_original_id: int


class ShopNew(CallbackData, prefix="shop_new"):
    pass


class Adv(CallbackData, prefix="adv"):
    adv_original_id: int
    action: str | None = "select"
    wb_user_cabinet_original_id: int | None = None


class TurnBot(CallbackData, prefix="turn_bot"):
    action: str
    adv_original_id: int | None = None
    wb_user_cabinet_original_id: int


class BotActive:
    action: bool


class Min_ctr(CallbackData, prefix="min_ctr"):  # noqa
    action: str
    adv_original_id: int
    wb_user_cabinet_original_id: int


class AddNewToken(CallbackData, prefix="add_new_token"):
    wb_user_cabinet_original_id: int


class DeleteWbUserCabinet(CallbackData, prefix="delete_wb_user_cabinet"):
    wb_user_cabinet_original_id: int


class SettingKeywords(CallbackData, prefix="setting_keywords"):
    adv_original_id: int
    type: str = "by_adv"
    page: int = 1
    reset_filter: bool = False


class SettingKeyword(CallbackData, prefix="setting_keyword"):
    keyword_setting_original_id: int


class ChangeKeywordHardStatus(CallbackData, prefix="change_keyword_hard_status"):
    new_hard_status: int
    keyword_setting_original_id: int


class ChangeKeywordTargetPlace(CallbackData, prefix="change_keyword_target_place"):
    keyword_setting_original_id: int


class CheckSubscribe(CallbackData, prefix="check_subscribe"):
    pass


class OrderSubscribe(CallbackData, prefix="order_subscribe"):
    period_days: int
    price: int
    wb_cabinet_original_id: int


class Start(CallbackData, prefix="start"):
    pass


class ConnectExistingAdvs(CallbackData, prefix="connect_existing_advs"):
    """Подключить существующие рекламные кампании WB к артикулу (NM-id)."""

    wb_user_cabinet_original_id: int


class ConnectExistingConfirmType1(CallbackData, prefix="ce_confirm_t1"):
    """Подтвердить выбор РК по первому типу (аукцион) или создать."""

    adv_id: int = 0  # 0 = нажата «Создать РК»


class ConnectExistingConfirmType2(CallbackData, prefix="ce_confirm_t2"):
    """Подтвердить выбор РК по второму типу (авто) или создать."""

    adv_id: int = 0  # 0 = нажата «Создать РК»


class ConnectExistingCreateBoth(CallbackData, prefix="ce_create_both"):
    """Подтверждение создания обеих кампаний (аукцион + авто) через create_complex_advs."""

    action: str = "confirm"  # confirm | cancel


class ConnectExistingContinueDespiteInvalid(CallbackData, prefix="ce_continue_inv"):
    """Продолжить создание при наличии только авто-РК без поиска (деактивация старых + create_complex_advs)."""

    action: str = "confirm"  # confirm | cancel


class ConnectExistingAdvsBackToShop(CallbackData, prefix="ce_back_shop"):
    """Вернуться в меню магазина из сценария «подключить существующие» (уже есть РК или отмена)."""

    wb_user_cabinet_original_id: int


class ShowShopsList(CallbackData, prefix="shops_list"):
    """Переход на страницу «Мои магазины» (список магазинов)."""

    pass


class ShopsListPaginator(CallbackData, prefix="shops_list_pg"):
    """Переключение страницы списка «Мои магазины»."""

    page: int


class Gate(CallbackData, prefix="gate"):
    """Коллбеки экрана гейта: invite_enter, pay_entry_amount, offer_open, restore_request."""

    action: str


class InviteShow(CallbackData, prefix="invite"):
    """Показать инвайт (для приглашения). Только для passed_gate."""

    action: str = "show"


class ChangeMaxCPC(CallbackData, prefix="change_max_cpc"):
    action: str
    adv_original_id: int

class ManageCampaignActivity(CallbackData, prefix="campaign_activity"):
    action: str
    adv_setting_original_id: int
    campaign_type: AdvType | None = None


class ChangeMinViewsForPredictCTR(
    CallbackData, prefix="change_min_views_for_predict_ctr"
):
    adv_setting_original_id: int


class AddBalance(CallbackData, prefix="add_balance"):
    wb_cabinet_original_id: int


class ConfirmAddBalance(CallbackData, prefix="confirm_add_balance"):
    wb_cabinet_original_id: int


class AddBalanceByCard(CallbackData, prefix="add_balance_by_card"):
    wb_cabinet_original_id: int


class AddBalanceFromUserBalance(CallbackData, prefix="add_balance_from_user_balance"):
    wb_cabinet_original_id: int


class AddUserBalance(CallbackData, prefix="add_user_balance"):
    pass


class ConfirmAddUserBalance(CallbackData, prefix="confirm_add_user_balance"):
    pass


class UserBalanceMenu(CallbackData, prefix="user_balance_menu"):
    """Открыть экран «Мой баланс» (баланс и бонусы пользователя)."""
    pass


class KeywordPositionHistory(CallbackData, prefix="keyword_position_history"):
    adv_original_id: int


class AddWhitePhrases(CallbackData, prefix="add_white_phrases"):
    adv_setting_id: int


class AddFixedPhrases(CallbackData, prefix="add_fixed_phrases"):
    adv_setting_id: int


class TurnParsing(CallbackData, prefix="turn_parsing"):
    action: str
    adv_original_id: int
    wb_user_cabinet_original_id: int


class CPMSettingMenu(CallbackData, prefix="cpm_setting"):
    action: str
    adv_original_id: int


class AddBlackPhrasesTemplates(CallbackData, prefix="add_black_phrases"):
    adv_setting_id: int


class ResetBlackPhrases(CallbackData, prefix="reset_black_phrases"):
    adv_setting_id: int


class DownloadCSV(CallbackData, prefix="download_csv"):
    adv_setting_original_id: int


class TurnClusters(CallbackData, prefix="turn_clusters"):
    action: str
    adv_original_id: int


class CheckPosition(CallbackData, prefix="check_position"):
    keyword_setting_original_id: int
    adv_original_id: int


class UpdateCompanyFromWB(CallbackData, prefix="update_company_from_wb"):
    wb_user_cabinet_original_id: int


class WBUpdate(CallbackData, prefix="wb_update"):
    action: str
    adv_setting_original_id: int


class ResetAddedClicks(CallbackData, prefix="reset_added_clicks"):
    adv_setting_original_id: int


# TODO(legacy-remove): legacy callback связан с target_ctr_mode, оставить
# до полного выпиливания старого интерфейса strategy_setting.
class StrategySetting(CallbackData, prefix="strategy_setting"):
    action: str
    adv_setting_original_id: int


class StrategyMenu(CallbackData, prefix="strategy_menu"):
    action: str
    adv_setting_original_id: int
    strategy: str | None = None


class ResetWhiteList(CallbackData, prefix="reset_white_list"):
    adv_setting_original_id: int


class AddRelevantPhrases(CallbackData, prefix="add_relevant_phrases"):
    adv_setting_id: int


class ChangeAutoMinCTR(CallbackData, prefix="change_auto_min_ctr"):
    action: str
    adv_setting_original_id: int


class ShowFavorites(CallbackData, prefix="show_favorites"):
    pass


class AddToFavorites(CallbackData, prefix="add_to_favorites"):
    adv_setting_original_id: int


class RemoveFromFavorites(CallbackData, prefix="remove_from_favorites"):
    adv_setting_original_id: int


class ChangeCPM(CallbackData, prefix="change_cpm"):
    adv_setting_original_id: int

    class DeleteWBUserCabinet(CallbackData, prefix="delete_wb_user_cabinet"):
        wb_user_cabinet_original_id: int


class ResetPlace(CallbackData, prefix="reset_place"):
    action: str
    adv_setting_original_id: int


class TurnWhiteListUpdate(CallbackData, prefix="turn_white_list_update"):
    action: str
    wb_cabinet_original_id: int


class OrdersSourceToggle(CallbackData, prefix="orders_source_toggle"):
    new_source: OrdersSourceForAutoMode
    adv_setting_original_id: int


class PredictCTRModeToggle(CallbackData, prefix="predict_ctr_mode_toggle"):
    new_mode: PredictCTRMode
    adv_setting_original_id: int


class TargetPositionModeToggle(CallbackData, prefix="target_position_mode_toggle"):
    new_mode: str  # value of TargetPositionMode (min_cpa / max_cart_to_views_conv)
    adv_setting_original_id: int


class SalesPredictMethodToggle(CallbackData, prefix="sales_predict_method_toggle"):
    new_method: FactMethods
    adv_setting_original_id: int


class AutoUpdaterVersionToggle(CallbackData, prefix="auto_updater_version_toggle"):
    new_version: int
    adv_setting_original_id: int


class ChangeAutoUpdateExponentStatus(
    CallbackData, prefix="change_auto_update_exponent"
):
    adv_id: int
    wb_user_cabinet_original_id: int
    new_status: bool


class ChangeAutoAddOnlyRelevantPhraseStatus(
    CallbackData, prefix="change_auto_add_relevant"
):
    adv_id: int
    wb_user_cabinet_original_id: int
    new_status: bool


class ChangeRecSystemModeStatus(CallbackData, prefix="change_rec_system_mode"):
    adv_id: int
    wb_user_cabinet_original_id: int
    new_status: bool


class AutoBudgetWatchdogToggle(CallbackData, prefix="auto_budget_watchdog_toggle"):
    adv_setting_original_id: int
    new_status: bool


class CommonBudgetModeToggle(CallbackData, prefix="common_budget_mode_toggle"):
    adv_setting_original_id: int
    new_status: bool


class IncrementalStatsToggle(CallbackData, prefix="incremental_stats_toggle"):
    adv_setting_original_id: int
    new_status: bool


class ChangeAuctionBidderActiveStatus(
    CallbackData, prefix="change_auction_bidder_active_status"
):
    adv_id: int
    wb_user_cabinet_original_id: int
    new_status: bool


class ChangeCommonBidInSearchAdvStatus(
    CallbackData, prefix="change_common_bid_in_search_adv_status"
):
    adv_id: int
    new_status: bool


class IndividualKeywordsTargetPlaceToggle(
    CallbackData, prefix="indiv_keywords_target_place_toggle"
):
    adv_id: int
    new_status: bool


class ApplyCampaignDefaults(CallbackData, prefix="apply_adv_defaults"):
    adv_setting_original_id: int
    wb_user_cabinet_original_id: int


class ChangeShopDefaultMaxCPM(CallbackData, prefix="change_shop_default_max_cpm"):
    wb_user_cabinet_original_id: int


class ApplyDefaultsForShop(CallbackData, prefix="apply_shop_defaults"):
    wb_user_cabinet_original_id: int
