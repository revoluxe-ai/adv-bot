"""Главное меню и список магазинов.

Invite/partner UX deferred: ``settings.invite_gate`` default False — кнопки
«Показать инвайт» / minimal presentation keyboard не показываются на текущем
rollout (см. invite-gate-deferred decision).
"""

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.client_bot.admin_access import is_bot_admin
from app.client_bot.user_interface.message_templates import TextWithKeyboard
from app.client_bot.user_interface.views import callbacks
from app.client_bot.user_interface.views.callbacks import Action
from app.client_bot.user_interface.views.callbacks import Gate
from app.client_bot.user_interface.views.get_main_text import get_main_text
from app.modules.cabinet_bonus_manager.callbacks import AdminPanel
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.settings import settings

SHOPS_LIST_PAGE_TITLE = (
    "Нажмите 'Добавить магазин' для начала использования\n"
    "Мои магазины: \n"
    "\n"
    "Префикс кнопки: [Каб][Ток] имя\n"
    "Каб — магазин в боте: ✅ активен / ❌ не активен\n"
    "Ток — токены: ✅ ок / ❌ замена токена\n"
)

SHOPS_PER_PAGE = 20


class MainMenu(TextWithKeyboard):
    """Главная после /start: free-меню (магазины/баланс/инвайт).

    Минимальный presentation-only keyboard оставлен только при явном
    ``PRESENTATION_ONLY_MODE=true`` и ``full_client_ui=False`` (legacy).
    """

    parse_mode = ParseMode.HTML

    def __init__(self, bot: Bot, chat_id: int, *, full_client_ui: bool = False):
        super().__init__(bot, chat_id)
        self.user_telegram_id = chat_id
        self._full_client_ui = full_client_ui

    @property
    def text(self) -> str:
        return get_main_text(self.user_telegram_id)

    @property
    def keyboard(self) -> InlineKeyboardMarkup:
        return get_main_menu_keyboard(
            self.user_telegram_id, full_client_ui=self._full_client_ui
        )


def get_main_menu_keyboard(
    user_telegram_id: int, *, full_client_ui: bool = False
) -> InlineKeyboardMarkup:
    """Клавиатура главной: full free UI по умолчанию.

    Legacy minimal («только Ввести инвайт») — только если
    ``presentation_only`` и не ``full_client_ui``.
    """
    keyboard_buttons: list[list[InlineKeyboardButton]] = []

    if settings.presentation_only and not full_client_ui:
        if is_bot_admin(user_telegram_id):
            admin_button = InlineKeyboardButton(
                text="Панель администратора",
                callback_data=AdminPanel(action="menu").pack(),
            )
            keyboard_buttons.append([admin_button])
        invite_button = InlineKeyboardButton(
            text="Ввести инвайт",
            callback_data=Gate(action="invite_enter").pack(),
        )
        keyboard_buttons.append([invite_button])
        return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    if is_bot_admin(user_telegram_id):
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
    # INVITE DEFERRED: partner-invite UX only when invite_gate re-enabled explicitly.
    if settings.invite_gate:
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
        page: int = 1,
    ):
        super().__init__(bot, chat_id)
        self.__all_shops = all_shops
        self.__shop_ids_with_active_tokens = shop_ids_with_active_tokens
        self._page = page
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
            page=self._page,
        )


def get_shops_list_keyboard(
    all_shops: list[WBUserCabinet],
    user_telegram_id: int,
    shop_ids_with_active_tokens: set[str] | None = None,
    page: int = 1,
) -> InlineKeyboardMarkup:
    """Клавиатура страницы «Мои магазины»: Добавить магазин, список, пагинация, Назад."""
    keyboard_buttons: list[list[InlineKeyboardButton]] = []

    add_shop_button = InlineKeyboardButton(
        text="➕Добавить магазин", callback_data=callbacks.ShopNew().pack()
    )
    keyboard_buttons.append([add_shop_button])

    start_index = (page - 1) * SHOPS_PER_PAGE
    end_index = start_index + SHOPS_PER_PAGE
    shops_slice = all_shops[start_index:end_index]

    for wb_user_cabinet in shops_slice:
        shop_name = wb_user_cabinet.name
        wb_user_cabinet_original_id: int = wb_user_cabinet.id
        wb_cabinet = wb_user_cabinet.wb_cabinet
        has_cabinet_active = hasattr(wb_cabinet, "active")
        cabinet_ok = getattr(wb_cabinet, "active", True) is True
        token_ok = shop_ids_with_active_tokens is None or (
            wb_cabinet.shop_id in shop_ids_with_active_tokens
        )
        cab_icon = "✅" if cabinet_ok else "❌"
        tok_icon = "✅" if token_ok else "❌"
        if has_cabinet_active:
            # Keep both cabinet/token indicators as documented in title.
            full_shop_name = f"{cab_icon}{tok_icon} {shop_name}"[:100]
        else:
            # Legacy fallback for partially-loaded objects used in tests/old flows.
            full_shop_name = f"{shop_name} {tok_icon}"[:100]
        button = InlineKeyboardButton(
            text=full_shop_name,
            callback_data=callbacks.Shop(
                action=Action.select,
                wb_user_cabinet_original_id=wb_user_cabinet_original_id,
            ).pack(),
        )
        keyboard_buttons.append([button])

    paginator_row: list[InlineKeyboardButton] = []
    if page > 1:
        paginator_row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=callbacks.ShopsListPaginator(page=page - 1).pack(),
            )
        )
    if len(all_shops) > end_index:
        paginator_row.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=callbacks.ShopsListPaginator(page=page + 1).pack(),
            )
        )
    if paginator_row:
        keyboard_buttons.append(paginator_row)

    balance_row = InlineKeyboardButton(
        text="Мой баланс",
        callback_data=callbacks.UserBalanceMenu().pack(),
    )
    keyboard_buttons.append([balance_row])
    if settings.invite_gate:
        invite_show_button = InlineKeyboardButton(
            text="Показать инвайт",
            callback_data=callbacks.InviteShow().pack(),
        )
        keyboard_buttons.append([invite_show_button])

    back_button = InlineKeyboardButton(
        text="Назад",
        callback_data=callbacks.Start().pack(),
    )
    keyboard_buttons.append([back_button])

    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)


class ShopChoice(ShopsListPage):
    """Алиас для обратной совместимости: показывает страницу списка магазинов."""

    pass
