from app.modules.common_slaves.wildberries.models import AdvSetting as _AdvSetting
from app.utils.db.session_maker import get_async_session_maker as _sm


async def get_adv_setting(adv_setting_original_id: int) -> _AdvSetting:
    async with _sm(read_only=True) as session:
        adv = await session.get(_AdvSetting, adv_setting_original_id)
        assert adv
        return adv
