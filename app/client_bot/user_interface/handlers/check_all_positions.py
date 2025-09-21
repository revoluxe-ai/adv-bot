import aiogram
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select

from app.modules.common_slaves.wildberries.models import AdvSetting, KeywordSetting
from app.modules.wb_keywords_parser.parser import fast_queue
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks

sm = get_async_session_maker

router = Router()


@router.callback_query(callbacks.CheckAllPositions.filter(F.action == "All"))
async def check_all_positions(
    callback: types.CallbackQuery,
    callback_data: callbacks.ChoiceAdvPaginator,
    bot: aiogram.Bot,
    state: FSMContext,
):
    adv_setting_original_id: int = callback_data.adv_original_id
    stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_original_id)

    async with sm() as session:
        keyword_settings = await session.execute(stmt)
        keyword_settings = keyword_settings.scalars().all()
    async with sm() as session:
        stmt = select(AdvSetting.nmids).where(AdvSetting.id == adv_setting_original_id)
        nmids = await session.execute(stmt)
        nmids: list[int] = nmids.scalar()
        for keyword_setting in keyword_settings:
            text = keyword_setting.text
            # ключ, id рекламной кампании, nmids, последние просмотры, максимальная страница для проверки
            task = (text, adv_setting_original_id, set(nmids), None, 60)
            await fast_queue.put(task)
