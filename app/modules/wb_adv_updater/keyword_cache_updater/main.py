from app.client_bot.utils import get_keywords_for_keyboard
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils import redis_manager


async def calculate_keywords_for_keyboard(
    adv_setting: AdvSetting,
) -> list[CalculatedKeyword]:
    keywords: list[CalculatedKeyword] = await get_keywords_for_keyboard(adv_setting)
    return keywords


async def update_to_cache(adv_setting: AdvSetting, keywords: list[CalculatedKeyword]):
    await redis_manager.set_keywords_for_keyboard(adv_setting.id, keywords)  # type: ignore[attr-defined]
