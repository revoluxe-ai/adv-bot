from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCard, WBCategory
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm


class AdvParameterManager:
    async def get_min_cpm(self, adv: AdvSetting) -> int:
        # TODO: Реализовать получение минимального CPM
        return 10
