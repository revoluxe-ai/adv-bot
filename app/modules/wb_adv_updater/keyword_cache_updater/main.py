from app.client_bot.utils import KeywordForKeyboard, get_keywords_for_keyboard
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils import redis_manager



async def calculate_keywords_for_keyboard(adv_setting: AdvSetting)-> list[KeywordForKeyboard]:
    keywords: list[KeywordForKeyboard] = await get_keywords_for_keyboard(adv_setting)
    return keywords




async def update_to_cache(adv_setting: AdvSetting, keywords: list[KeywordForKeyboard]):
    await redis_manager.set_keywords_for_keyboard(adv_setting.id, keywords)



