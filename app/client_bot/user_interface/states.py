from aiogram.filters.state import State, StatesGroup


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
   waiting_for_filter_keywords = State()


class ChangeMaxCPC(StatesGroup):
    waiting_for_new_max_cpc = State()


class ChangeMinViewsForPredictCTR(StatesGroup):
    waiting_for_new_min_views = State()


class AddBalance(StatesGroup):
    awaiting_amount = State()


class AdvCompanyCatalog(StatesGroup):
    waiting_for_keywords_for_filter = State()