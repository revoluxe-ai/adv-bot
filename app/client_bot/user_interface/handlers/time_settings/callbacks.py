from aiogram.filters.callback_data import CallbackData


class TS(CallbackData, prefix="ts"):
    a: str
    adv: int | None = None
    dow: int | None = None
    h: int | None = None
    v: str | None = None
    sid: str | None = None
