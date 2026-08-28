"""Telegram callback-схемы для client bot UI.

Модуль хранит aiogram ``CallbackData`` для экранов Telegram-интерфейса и
компактные коды для action-полей, чтобы не упираться в лимит 64 байта у
callback_data.
"""

from aiogram.filters.callback_data import CallbackData

from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode
from app.shared.domains.wb.enums import (
    AdvType,
)


_AUTO_SHELF_BID_CONTROL_ACTION_CODES: dict[str, str] = {
    "open": "o",
    "refresh": "r",
    "enable": "e",
    "disable": "d",
    "settings": "s",
    "set_max_bid": "mb",
    "set_test_share": "ts",
    "set_target_test_impressions": "tti",
    "set_target_test_observation_minutes": "tto",
    "set_min_bid_distance": "md",
    "set_retest_interval_days": "rid",
    "strategy_menu": "sm",
    "set_strategy_plan_distance": "sp",
    "set_strategy_ctr": "sc",
    "set_strategy_cpc": "sk",
    "reset_cycle": "rc",
    "force_main": "fm",
    "back": "b",
}
_AUTO_SHELF_BID_CONTROL_ACTION_NAMES: dict[str, str] = {
    code: name for name, code in _AUTO_SHELF_BID_CONTROL_ACTION_CODES.items()
}


def compact_auto_shelf_bid_control_action(action: str) -> str:
    """Сжать action для Telegram callback_data.

    Args:
        action: Полное имя действия, используемое в коде обработчиков.

    Returns:
        Короткий код, если для action есть компактное представление, иначе
        исходное значение.
    """
    return _AUTO_SHELF_BID_CONTROL_ACTION_CODES.get(action, action)


def normalize_auto_shelf_bid_control_action(action: str) -> str:
    """Восстановить полное имя action из compact callback_data.

    Args:
        action: Значение, пришедшее из callback_data.

    Returns:
        Полное имя действия для маршрутизации. Старые длинные значения
        возвращаются без изменений.
    """
    return _AUTO_SHELF_BID_CONTROL_ACTION_NAMES.get(action, action)


class ChoiceAdvPaginator(CallbackData, prefix="choice_adv_paginator"):
    wb_user_cabinet_original_id: int
    page: int
    reset_filter: bool = False


class UiModeToggle(CallbackData, prefix="ui_mode_toggle"):
    """Toggle the admin-selected UI mode between free and paid."""

    wb_user_cabinet_original_id: int


class Action:
    new = "new"
    select = "select"
    buy = "buy"


class BudgetForCreatingAdv(CallbackData, prefix="budget"):
    type: str


class Shop(CallbackData, prefix="shop"):
    action: str
    wb_user_cabinet_original_id: int


class ShopMassAdvOpsMenu(CallbackData, prefix="shop_mass_adv_ops_menu"):
    wb_user_cabinet_original_id: int


class ShopMassAdvOpsBack(CallbackData, prefix="shop_mass_adv_ops_back"):
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


class AutoManagementLanding(CallbackData, prefix="auto_mgmt_landing"):
    """Коллбеки paid-landing автоуправления рекламой в меню кампании."""

    action: str
    adv_setting_original_id: int
    wb_user_cabinet_original_id: int


class MinusPhrasesSetting(CallbackData, prefix="minus_phrases_setting"):
    """Коллбеки экрана настройки фонового обновления минус-фраз."""
    action: str
    adv_setting_original_id: int
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


class KeywordsDailyStats(CallbackData, prefix="kw_daily_stats"):
    """Пагинация дневной статистики на странице ключей."""

    adv_original_id: int
    page: int = 1
    keywords_page: int = 1
    sort_mode: str = "by_adv"


class SettingKeyword(CallbackData, prefix="setting_keyword"):
    keyword_setting_original_id: int


class KeywordDailyHistory(CallbackData, prefix="kw_day_hist"):
    """Пагинация дневной истории по одному ключу."""

    keyword_setting_original_id: int
    page: int = 1


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


class ConnectExistingChooseAuction(CallbackData, prefix="ce_choose_auc"):
    """Выбор способа выбора аукционной РК: ввести ID, список, создать, назад."""

    action: str  # enter_id | choose_list | create | back


class ConnectExistingChooseAuto(CallbackData, prefix="ce_choose_auto"):
    """Выбор способа выбора авто-РК: ввести ID, список, создать, назад."""

    action: str  # enter_id | choose_list | create | back


class ConnectExistingCreateBoth(CallbackData, prefix="ce_create_both"):
    """Подтверждение создания обеих кампаний (аукцион + авто) через create_complex_advs."""

    action: str = "confirm"  # confirm | cancel


class ConnectExistingContinueDespiteInvalid(CallbackData, prefix="ce_continue_inv"):
    """Продолжить создание при наличии только авто-РК без поиска (деактивация старых + create_complex_advs)."""

    action: str = "confirm"  # confirm | cancel


class ConnectExistingAdvsBackToShop(CallbackData, prefix="ce_back_shop"):
    """Вернуться в меню магазина из сценария «подключить существующие» (уже есть РК или отмена)."""

    wb_user_cabinet_original_id: int


class ConnectExistingChangeNmid(CallbackData, prefix="ce_change_nmid"):
    """Ввести другой артикул в сценарии «подключить существующие»."""

    wb_user_cabinet_original_id: int


class ConnectExistingCardNotFound(CallbackData, prefix="ce_card_not_found"):
    """Действие при «артикул по фильтру не найден»: поиск по полному списку или выход."""

    action: str  # retry_full_list


class ShowShopsList(CallbackData, prefix="shops_list"):
    """Переход на страницу «Мои магазины» (список магазинов)."""

    pass


class ShopsListPaginator(CallbackData, prefix="shops_list_pg"):
    """Переключение страницы списка «Мои магазины»."""

    page: int


class Gate(CallbackData, prefix="gate"):
    """Коллбеки экрана гейта: invite_enter, offer_open, restore_request."""

    action: str


class RequestPresentation(CallbackData, prefix="presentation"):
    """Запрос презентации: после ввода валидного инвайта — уведомление саппорту."""

    action: str = "request"


class InviteShow(CallbackData, prefix="invite"):
    """Показать инвайт (для приглашения). Только для passed_gate."""

    action: str = "show"


class PartnerAdminAction(CallbackData, prefix="partner_admin"):
    """Admin callbacks for partner statistics and partner payouts."""

    action: str
    partner_user_id: int | None = None
    page: int | None = None
    sort_key: str | None = None


class ChangeAutoBid(CallbackData, prefix="change_auto_bid"):
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


class RaiseCardAnalyze(CallbackData, prefix="raise_card_analyze"):
    """Анализ раскрутки карточки: меню, результат, по дням, бакеты, что делать дальше."""

    adv_setting_original_id: int
    action: str | None = "menu"  # menu | result | by_days | buckets | what_next
    nmid: int | None = None


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


class AutoShelfBidControlBidPoints(CallbackData, prefix="asbc_bp"):
    """Навигация по покрытым ставкам текущего цикла (Telegram-просмотрщик).

    ``index`` — номер страницы (0-based), до 10 строк на странице.
    """

    adv_setting_original_id: int
    index: int = 0


class AutoShelfBidControlMenu(CallbackData, prefix="auto_shelf_bid_ctrl"):
    """Действия экрана управления ставкой полок Auto-РК.

    Поддерживаемые action:
        open, refresh,
        enable, disable, settings,
        set_max_bid, set_test_share, set_target_test_impressions, set_min_bid_distance,
        reset_cycle, force_main,
        back.

    Для новых кнопок action кодируется в compact-формате, чтобы callback_data
    не превышал лимит Telegram; старые длинные значения остаются совместимы в
    обработчиках.
    """

    action: str
    adv_setting_original_id: int


class AddBlackPhrasesTemplates(CallbackData, prefix="add_black_phrases"):
    adv_setting_id: int


class ResetBlackPhrases(CallbackData, prefix="reset_black_phrases"):
    adv_setting_id: int


class TestBlackPhrasesTemplates(CallbackData, prefix="test_black_phrases"):
    adv_setting_id: int


class ExitBlackPhrasesTest(CallbackData, prefix="exit_black_phrases_test"):
    adv_setting_id: int


class ExportBlackPhrases(CallbackData, prefix="export_black_phrases"):
    adv_setting_id: int


class AddRelevantPhraseTemplates(CallbackData, prefix="add_rel_phrase_tpl"):
    adv_setting_id: int


class ResetRelevantPhraseTemplates(CallbackData, prefix="reset_rel_phrase_tpl"):
    adv_setting_id: int


class TestRelevantPhraseTemplates(CallbackData, prefix="test_rel_phrase_tpl"):
    adv_setting_id: int


class ExitRelevantPhraseTemplatesTest(CallbackData, prefix="exit_rel_phrase_test"):
    adv_setting_id: int


class ExportRelevantPhraseTemplates(CallbackData, prefix="export_rel_phrase_tpl"):
    adv_setting_id: int


class DownloadCSV(CallbackData, prefix="download_csv"):
    adv_setting_original_id: int


class ExportShopAdvExcel(CallbackData, prefix="shop_adv_excel_export"):
    """Выгрузка всех активных РК магазина в один Excel (меню магазина)."""

    wb_user_cabinet_original_id: int


class ImportShopAdvExcel(CallbackData, prefix="shop_adv_excel_import"):
    """Загрузка Excel с правками по магазину; далее ожидается документ в FSM."""

    wb_user_cabinet_original_id: int


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


class ResetNonRelevantPhrases(CallbackData, prefix="reset_non_rel"):
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


class V3RolloutAggMenuOpen(CallbackData, prefix="v3_rollout_agg_menu_open"):
    adv_setting_original_id: int


class V3RolloutAggMenuBack(CallbackData, prefix="v3_rollout_agg_menu_back"):
    pass


class V3RolloutAggSet(CallbackData, prefix="v3_rollout_agg_set"):
    adv_setting_original_id: int
    level: int


class V3CalibrationStepChange(CallbackData, prefix="v3_cal_step_change"):
    adv_setting_original_id: int


class V3TickReportOpen(CallbackData, prefix="v3_tick_report_open"):
    adv_setting_original_id: int


class V3TickReportRefresh(CallbackData, prefix="v3_tick_report_refresh"):
    adv_setting_original_id: int


class V3TickReportBack(CallbackData, prefix="v3_tick_report_back"):
    adv_setting_original_id: int


class KeywordV3DecisionTraceOpen(CallbackData, prefix="kw_v3_dec_open"):
    """Открыть экран последнего V3-решения по ключу (admin debug)."""

    keyword_setting_original_id: int
    page: int = 1


class KeywordV3DecisionTraceRefresh(CallbackData, prefix="kw_v3_dec_refresh"):
    """Обновить экран последнего V3-решения по ключу."""

    keyword_setting_original_id: int
    page: int = 1


class KeywordV3DecisionTraceBack(CallbackData, prefix="kw_v3_dec_back"):
    """Вернуться к карточке ключа из экрана V3-решения."""

    keyword_setting_original_id: int
    page: int = 1


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


class ManageRelevantAndNonRelevantPhrases(
    CallbackData, prefix="manage_rel_nonrel_phrases"
):
    adv_setting_original_id: int


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


class AutoCommonBudgetToggle(CallbackData, prefix="auto_common_budget_toggle"):
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


class SetCommonBidManual(CallbackData, prefix="set_common_bid_manual"):
    adv_setting_original_id: int
    wb_user_cabinet_original_id: int


class RebindAdvCampaignIds(CallbackData, prefix="rebind_adv_ids"):
    """Перепривязка кампаний WB: поле adv_id (авто) и колонка _search_adv_id (поиск)."""

    action: str  # menu | auto | search | back
    adv_setting_original_id: int
    wb_user_cabinet_original_id: int


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


class ResetShopNonRelevantPhrases(CallbackData, prefix="reset_shop_non_rel"):
    wb_user_cabinet_original_id: int


class ToggleCabinetActive(CallbackData, prefix="toggle_cabinet_active"):
    """Переключить WBCabinet.active из меню магазина."""

    wb_user_cabinet_original_id: int
