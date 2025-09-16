from aiogram.fsm.state import StatesGroup, State


class CreateCompamyStates(StatesGroup):
    waiting_for_get_nmid = State()
