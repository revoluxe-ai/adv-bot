import asyncio
import os
from pathlib import Path

import pytest

from aiogram import Bot
from dotenv import load_dotenv

from app.modules.wb_adv_updater.modules.balance_exp_informer.dto import ReminderItem
from app.modules.wb_adv_updater.modules.balance_exp_informer.levels import pick_level
from app.modules.wb_adv_updater.modules.balance_exp_informer.message_builder import (
    build_message,
)
from python_modules.path_setting_funcs import find_project_root

PROJECT_ROOT = find_project_root(Path(__file__).resolve())

load_dotenv(PROJECT_ROOT / ".env")


load_dotenv(".env")


@pytest.mark.parametrize(
    "days_left",
    [
        -1.0,  # EXPIRED
        0.2,  # D1: меньше суток
        1.2,  # D3: меньше 3 дней
        2.9,  # D3: меньше 3 дней
    ],
)
@pytest.mark.asyncio
async def test_send_balance_reminder_integration(days_left: float):
    token = os.environ.get("TEST_TELEGRAM_BOT_TOKEN")
    if not token:
        pytest.skip("TEST_TELEGRAM_BOT_TOKEN is not set")

    chat_id_raw = os.environ.get("TEST_TELEGRAM_CHAT_ID")
    if not chat_id_raw:
        pytest.skip("TEST_TELEGRAM_CHAT_ID is not set")

    chat_id = int(chat_id_raw)

    level = pick_level(days_left)
    if level is None:
        pytest.skip("days_left is outside of reminder zone")

    bot = Bot(token=token)
    try:
        reminder = ReminderItem(
            reminder_id=1,
            wb_cabinet_id=1,
            shop_id="integration-shop",
            shop_name="integration-shop",
            level=int(level),
            balance=0.0,
            avg_daily_spend=1.0,
            days_left=days_left,
        )

        text, keyboard = build_message([reminder])

        # регресс: никаких "0 дн."
        assert "0 дн." not in text

        response = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
        )
        assert hasattr(response, "message_id")
    finally:
        await bot.session.close()
    await asyncio.sleep(1)