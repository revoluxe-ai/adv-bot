from .into_callback import CreateNewAdv as CreateNewAdvCallback


__all__ = ['button']


from aiogram.types import InlineKeyboardButton



def get_telegram_button( wb_user_cabinet_original_id, ):
    button = InlineKeyboardButton(text='Создать рекламную кампанию',
                                  callback_data=CreateNewAdvCallback(
                                        wb_user_cabinet_original_id=1,
                                        adv_id=1
                                    ).to_str())

    return button

