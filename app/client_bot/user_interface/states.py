from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.state import State, StatesGroup


class GlobalState(StatesGroup):
    shop_choice = State()

class CabinetRegistration(StatesGroup):
    cabinet_name = State()
    api = State()



class ChangeMinCTR(StatesGroup):
    waiting_for_new_min_ctr = State()


class AddNewToken(StatesGroup):
    token = State()


class CreateNewAdvCompany(StatesGroup):
    waiting_for_name = State()
    waiting_for_nmids = State()


class RefProgram(StatesGroup):
    getting_name = State()



class AdvSetting(StatesGroup):
   waiting_for_filter_by_query = State()
   waiting_for_filter_keywords = State()


class ChangeMaxCPC(StatesGroup):
    waiting_for_new_max_cpc = State()


class ChangeMinViewsForPredictCTR(StatesGroup):
    waiting_for_new_min_views = State()


class AddBalance(StatesGroup):
    awaiting_confirmation = State()
    awaiting_amount = State()


class AdvCompanyCatalog(StatesGroup):
    waiting_for_keywords_for_filter = State()
    waiting_for_sort_type = State()


class AddWhitePhrases(StatesGroup):
    waiting_for_white_phrases = State()


class CPMSetting(StatesGroup):
    waiting_for_min_position = State()
    waiting_for_max_cpm = State()
    waiting_for_manual_cpm = State()
    waiting_for_max_position = State()


class AddBlackPhrasesTemplates(StatesGroup):
    waiting_for_black_phrases = State()


class AddRelevantPhrases(StatesGroup):
    waiting_for_relevant_phrases = State()


class ChangeCPM(StatesGroup):
    waiting_for_cpm = State()


class ShopMenuState(StatesGroup):
    shop_menu = State()
