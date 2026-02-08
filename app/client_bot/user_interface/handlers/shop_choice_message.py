from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot import const
from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import Action
from app.client_bot.user_interface.views.get_main_text import get_main_text
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel
from app.modules.common_slaves.wildberries.models import WBUserCabinet

SHOPS_LIST_PAGE_TITLE = ("Мои магазины: \n"
                         ""
                         "✅ - Магазин подключен\n"
                         "❌ - Требуется замена токена\n")


class MainMenu(TextWithKeyboard):
    """Главная страница после Start: «Мои магазины», инвайт, баланс, админка."""

    parse_mode = ParseMode.HTML

    def __init__(self, bot: Bot, chat_id: int):
        super().__init__(bot, chat_id)
        self.user_telegram_id = chat_id

    @property
    def text(self) -> str:
        return get_main_text(self.user_telegram_id)

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return get_main_menu_keyboard(self.user_telegram_id)


def get_main_menu_keyboard(user_telegram_id: int) -> InlineKeyboardMarkup:
    """Клавиатура главной страницы: Мои магазины, Показать инвайт, Мой баланс, админка."""
    keyboard_buttons = []

    if user_telegram_id in const.ADMINS:
        admin_button = InlineKeyboardButton(
            text="Панель администратора",
            callback_data=AdminPanel(action="menu").pack(),
        )
        keyboard_buttons.append([admin_button])

    my_shops_button = InlineKeyboardButton(
        text="Мои магазины",
        callback_data=callbacks.ShowShopsList().pack(),
    )
    keyboard_buttons.append([my_shops_button])

    user_balance_button = InlineKeyboardButton(
        text="Мой баланс",
        callback_data=callbacks.UserBalanceMenu().pack(),
    )
    keyboard_buttons.append([user_balance_button])

    invite_show_button = InlineKeyboardButton(
        text="Показать инвайт",
        callback_data=callbacks.InviteShow().pack(),
    )
    keyboard_buttons.append([invite_show_button])


    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


class ShopsListPage(TextWithKeyboard):
    """Страница «Мои магазины»: Добавить магазин, список магазинов, Назад."""

    parse_mode = ParseMode.HTML

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        all_shops: list[WBUserCabinet],
        shop_ids_with_active_tokens: set[str] | None = None,
    ):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops
        self.__shop_ids_with_active_tokens = shop_ids_with_active_tokens
        self.user_telegram_id = chat_id

    @property
    def text(self) -> str:
        return SHOPS_LIST_PAGE_TITLE

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return get_shops_list_keyboard(
            self.__all_shops,
            self.user_telegram_id,
            self.__shop_ids_with_active_tokens,
        )


def get_shops_list_keyboard(
    all_shops: list[WBUserCabinet],
    user_telegram_id: int,
    shop_ids_with_active_tokens: set[str] | None = None,
) -> InlineKeyboardMarkup:
    """Клавиатура страницы «Мои магазины»: Добавить магазин, список, Назад."""
    keyboard_buttons = []

    add_shop_button = InlineKeyboardButton(
        text="➕Добавить магазин", callback_data=callbacks.ShopNew().pack()
    )
    keyboard_buttons.append([add_shop_button])

    for wb_user_cabinet in all_shops:
        shop_name = wb_user_cabinet.name
        wb_user_cabinet_original_id: int = wb_user_cabinet.id
        wb_cabinet = wb_user_cabinet.wb_cabinet
        is_active = bool(
            wb_cabinet.active
            and (
                shop_ids_with_active_tokens is None
                or wb_cabinet.shop_id in shop_ids_with_active_tokens
            )
        )
        status_text = "✅" if is_active else "❌"
        full_shop_name = f"{shop_name} {status_text}" + ' ' * 1000
        full_shop_name = full_shop_name[:30]
        button = InlineKeyboardButton(
            text=full_shop_name,
            callback_data=callbacks.Shop(
                action=Action.select,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            ).pack(),
        )
        keyboard_buttons.append([button])

    back_button = InlineKeyboardButton(
        text="Назад",
        callback_data=callbacks.Start().pack(),
    )
    keyboard_buttons.append([back_button])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


class ShopChoice(ShopsListPage):
    """Алиас для обратной совместимости: показывает страницу списка магазинов."""

    pass
