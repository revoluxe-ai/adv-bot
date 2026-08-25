from aiogram.fsm.state import State, StatesGroup


class GlobalState(StatesGroup):
    shop_choice = State()


class CabinetRegistration(StatesGroup):
    cabinet_name = State()
    api = State()


class AddNewToken(StatesGroup):
    token = State()


class CreateNewAdvCompany(StatesGroup):
    waiting_for_name = State()
    waiting_for_nmids = State()


class AdvSetting(StatesGroup):
    waiting_for_filter_by_query = State()
    waiting_for_filter_keywords = State()

class KeywordTargetPlace(StatesGroup):
    waiting_for_new_target_place = State()


class ChangeAutoBid(StatesGroup):
    waiting_for_new_bid = State()


class ChangeMinViewsForPredictCTR(StatesGroup):
    waiting_for_new_min_views = State()


class AddBalance(StatesGroup):
    awaiting_confirmation = State()
    awaiting_payment_method = State()
    awaiting_amount = State()


class AddUserBalance(StatesGroup):
    awaiting_amount = State()


class AdvCompanyCatalog(StatesGroup):
    waiting_for_keywords_for_filter = State()
    waiting_for_sort_type = State()


class AddWhitePhrases(StatesGroup):
    waiting_for_white_phrases = State()


class AddFixedPhrases(StatesGroup):
    waiting_for_fixed_phrases = State()


class CPMSetting(StatesGroup):
    waiting_for_min_position = State()
    waiting_for_max_cpm = State()
    waiting_for_manual_cpm = State()
    waiting_for_max_position = State()
    waiting_for_target_place_workbook = State()


class AddBlackPhrasesTemplates(StatesGroup):
    waiting_for_black_phrases = State()
    waiting_for_black_phrases_test = State()


class AddRelevantPhrases(StatesGroup):
    waiting_for_relevant_phrases = State()


class AddRelevantPhraseTemplatesGroup(StatesGroup):
    waiting_for_relevant_phrase_templates = State()
    waiting_for_relevant_phrase_templates_test = State()


class ChangeCPM(StatesGroup):
    waiting_for_cpm = State()


class SetCommonBidManual(StatesGroup):
    waiting_for_bid = State()


class RebindCampaignIds(StatesGroup):
    """Ручной ввод новых adv_id и search_adv_id для AdvSetting."""

    waiting_for_auto_adv_id = State()
    waiting_for_search_adv_id = State()


class ShopDefaultMaxCPM(StatesGroup):
    waiting_for_new_default_max_cpm = State()


class ShopMenuState(StatesGroup):
    shop_menu = State()


class CampaignActivity(StatesGroup):
    waiting_for_new_limit = State()


class GateInvite(StatesGroup):
    """Ввод инвайт-кода на экране гейта."""

    waiting_code = State()


class PresentationRequest(StatesGroup):
    """Ввод инвайт-кода для заявки на презентацию (одноразовый инвайт)."""

    waiting_invite = State()


class AdminGrantGate(StatesGroup):
    """Админ: открыть гейт пользователю по Telegram ID."""

    waiting_telegram_id = State()


class AdminResetUserAccess(StatesGroup):
    """Админ: сбросить доступ пользователя по Telegram ID."""

    waiting_telegram_id = State()


class AdminPartnerPayout(StatesGroup):
    """Админ: ввод суммы выплаты партнёру."""

    waiting_amount = State()


class AdminPartnerList(StatesGroup):
    """РђРґРјРёРЅ: СЌРєСЂР°РЅ СЃРїРёСЃРєР° РїР°СЂС‚РЅС‘СЂРѕРІ, РѕР¶РёРґР°РЅРёРµ С„РёР»СЊС‚СЂР°."""

    waiting_filter = State()


class AdvExcelRoundtrip(StatesGroup):
    """Ожидание .xlsx для импорта настроек РК."""

    waiting_for_workbook = State()


class ConnectExistingAdvsStates(StatesGroup):
    """Подключение существующих рекламных кампаний WB по NM-id."""

    waiting_nmid = State()
    confirm_type1 = State()  # показать РК по первому типу или «Создать РК»
    confirm_type2 = State()  # показать РК по второму типу или «Создать РК»
    waiting_auction_adv_id = State()  # ввод ID поисковой (аукцион) кампании
    waiting_auto_adv_id = State()  # ввод ID авто-кампании
    waiting_confirm_create_both = State()  # обе отсутствуют — подтверждение create_complex_advs
    waiting_confirm_continue_invalid = State()  # только авто без поиска — продолжить создание (деактивация + create)


class AutoShelfBidControlFSM(StatesGroup):
    """FSM ввода параметров для Telegram-управления ставкой в полках."""

    waiting_for_max_bid = State()
    waiting_for_test_share = State()
    waiting_for_target_test_impressions = State()
    waiting_for_target_test_observation_minutes = State()
    waiting_for_min_bid_distance = State()
    waiting_for_retest_interval_days = State()
