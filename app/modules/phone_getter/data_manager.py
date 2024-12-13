from app.core.data_manager.base import BaseDataManager
from app.core.data_manager.mixins.telegram_user import TelegramUserMixin


class DataManager(BaseDataManager, TelegramUserMixin):
    pass


