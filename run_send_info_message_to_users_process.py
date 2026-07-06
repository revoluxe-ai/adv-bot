"""CLI entry point for sending informational messages to users."""

import asyncio

import dotenv

from python_modules.logger import setup_logging

dotenv.load_dotenv()


if __name__ == "__main__":
    setup_logging()
    from app.modules.wb_adv_updater.runner import sender_message_to_not_pay_users

    asyncio.run(sender_message_to_not_pay_users())
