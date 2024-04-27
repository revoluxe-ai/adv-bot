from aiogram.filters.state import State, StatesGroup


class GlobalState(StatesGroup):
    shop_choice = State()

class CabinetRegistration(StatesGroup):
    cabinet_name = State()
    api = State()



class ChangeMinCTR(StatesGroup):
    min_ctr = State()


class AddNewToken(StatesGroup):
    token = State()


class CreateNewAdvCompany(StatesGroup):
    waiting_for_name = State()
    waiting_for_nmids = State()


class RefProgram(StatesGroup):
    getting_name = State()