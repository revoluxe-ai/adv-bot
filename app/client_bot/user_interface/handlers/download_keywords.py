import logging
import tempfile

import aiogram
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery
from sqlalchemy.future import select

from app.client_bot import utils
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker

from ..views import callbacks

logger = logging.getLogger(__name__)


router = Router()


_sm = get_async_session_maker


@router.callback_query(callbacks.DownloadCSV.filter())
async def setting_keywords_active_keywords(
    callback: CallbackQuery,
    callback_data: callbacks.DownloadCSV,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    await state.update_data(keywords_filter=None)
    adv_original_id = callback_data.adv_setting_original_id
    async with _sm() as session:
        stmt = select(AdvSetting).where(AdvSetting.id == adv_original_id)
        result = await session.execute(stmt)
        adv_setting: AdvSetting | None = result.scalar_one_or_none()
        if adv_setting is None:
            # Отправьте сообщение об ошибке пользователю или запишите в лог
            await bot.send_message(callback.from_user.id, "Настройка рекламы не найдена.")
            return

    csv_string: str = await utils.get_csv_file(adv_setting)

    # Создание временного файла для CSV
    with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv", encoding="utf-8") as temp_file:
        temp_file.write(csv_string)
        temp_file.flush()  # Сбрасываем буфер на диск
        temp_file.seek(0)  # Перемещаем указатель в начало файла
        file_name = f"{adv_setting.name}.csv"

        # Чтение данных из файла для BufferedInputFile
        with open(temp_file.name, "rb") as f:
            file_data = f.read()

        # Отправка файла пользователю
        await bot.send_document(
            chat_id=callback.from_user.id,
            document=BufferedInputFile(file_data, file_name),
        )

    # Удаление временного файла (опционально, т.к. NamedTemporaryFile с delete=False сам себя удалит)
    temp_file.close()
