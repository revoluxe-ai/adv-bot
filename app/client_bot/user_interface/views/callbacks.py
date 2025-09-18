from aiogram.filters.callback_data import CallbackData


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


class Min_ctr(CallbackData, prefix="min_ctr"):
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


class CheckSubscribe(CallbackData, prefix="check_subscribe"):
    pass


class RefProgram(CallbackData, prefix="ref_program"):
    """select or new"""

    action: str


class OrderSubscribe(CallbackData, prefix="order_subscribe"):
    period_days: int
    price: int
    wb_cabinet_original_id: int


class Start(CallbackData, prefix="start"):
    pass


class ChangeMinCTR(CallbackData, prefix="change_min_ctr"):
    action: str
    adv_original_id: int


class ChangeMaxCPC(CallbackData, prefix="change_max_cpc"):
    action: str
    adv_original_id: int


class ChangeMinViewsForPredictCTR(CallbackData, prefix="change_min_views_for_predict_ctr"):
    adv_setting_original_id: int


class AddBalance(CallbackData, prefix="add_balance"):
    wb_cabinet_original_id: int


class ConfirmAddBalance(CallbackData, prefix="confirm_add_balance"):
    wb_cabinet_original_id: int


class KeywordPositionHistory(CallbackData, prefix="keyword_position_history"):
    adv_original_id: int


class AddWhitePhrases(CallbackData, prefix="add_white_phrases"):
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


class StrategySetting(CallbackData, prefix="strategy_setting"):
    action: str
    adv_setting_original_id: int


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
