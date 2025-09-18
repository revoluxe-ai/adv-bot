from aiogram.fsm.state import State, StatesGroup


class CreateCompamyStates(StatesGroup):
    waiting_for_get_nmid = State()
