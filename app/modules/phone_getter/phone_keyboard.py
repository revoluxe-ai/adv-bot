from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def request_phone_button() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Нажмите сюда, чтобы отправить свой контакт менеджеру",
                            request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )