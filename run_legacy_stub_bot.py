import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError

# === CONFIG ===
LEGACY_BOT_TOKEN = os.getenv("LEGACY_BOT_TOKEN")
MAIN_BOT_USERNAME = "wb_sky_bot"  # без @
LEGACY_ID = "bot2"  # любое имя/ид, чтобы понимать источник в start payload

router = Router()

def redirect_kb() -> InlineKeyboardMarkup:
    url = f"https://t.me/{MAIN_BOT_USERNAME}?start=from_{LEGACY_ID}"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="➡️ Перейти в основной бот", url=url)]]
    )

REDIRECT_TEXT = (
    "Я перенёс управление и оплату в один основной бот — так уведомления и кабинеты не теряются."
    " Все данные и балансы сохранены\n\n"
    "Нажмите кнопку ниже 👇"
)

async def send_redirect(chat_id: int, bot: Bot) -> None:
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=REDIRECT_TEXT,
            reply_markup=redirect_kb(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except TelegramForbiddenError:
        # пользователь не начинал диалог / заблокировал — молча игнорируем
        return

# Ловим ЛЮБОЕ сообщение
@router.message()
async def any_message(m: Message, bot: Bot):
    await send_redirect(m.chat.id, bot)

# Ловим ЛЮБОЙ callback (если у тебя в старом боте были кнопки)
@router.callback_query()
async def any_callback(c: CallbackQuery, bot: Bot):
    # быстро подтверждаем, чтобы Telegram не крутил “часики”
    await c.answer()
    await send_redirect(c.message.chat.id if c.message else c.from_user.id, bot)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=LEGACY_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    # Важно: не подключай другие роутеры/хэндлеры/команды.
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
