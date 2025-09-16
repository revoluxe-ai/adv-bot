import dotenv

dotenv.load_dotenv()
import asyncio

from app.modules.wb_adv_updater.runner import sender_message_to_not_pay_users
from python_modules.logger import setup_logging

setup_logging()



if __name__ == '__main__':
    asyncio.run(sender_message_to_not_pay_users())
