from aiogram.filters.callback_data import CallbackData


class ChangePlanSetting(CallbackData, prefix="change-plan-setting"):
    adv_id: int
    target_point: str


class V3RaiseMaxCpoToggle(CallbackData, prefix="v3_raise_max_cpo_toggle"):
    adv_id: int
    new_status: bool


class RaisePlanOnPromobonusesToggle(CallbackData, prefix="raise_plan_on_promobonuses"):
    adv_id: int
    new_status: bool
