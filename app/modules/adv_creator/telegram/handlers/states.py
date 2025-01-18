from app import ao


class CreateCompamyStates(ao.state.StatesGroup):
    waiting_for_get_nmid = ao.state.State()
