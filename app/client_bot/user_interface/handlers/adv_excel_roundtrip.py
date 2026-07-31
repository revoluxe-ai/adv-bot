"""Excel: выгрузка / загрузка настроек активных РК по магазину (меню магазина)."""

from __future__ import annotations

import io
from datetime import datetime
import math
import logging

import aiogram
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from app.client_bot.user_interface import states
from app.client_bot.user_interface.services.adv_excel_roundtrip.export_build import (
    build_adv_excel_export,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.excel_io import (
    read_adv_excel_upload,
    write_adv_excel_workbook,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.import_apply import (
    apply_adv_excel_rows,
    verify_user_owns_wb_user_cabinet,
)
from app.modules.sales_plan_settings.v3_raise_max_cpo import (
    format_v3_raise_max_auto_disable_message,
)
from app.client_bot.user_interface.views import callbacks

router = Router()
logger = logging.getLogger(__name__)


class _ProgressReporter:
    def __init__(
        self, *, bot: aiogram.Bot, chat_id: int, title: str, min_step: int = 10
    ) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._title = title
        self._min_step = min_step
        self._last_sent = 0
        self._last_percent_bucket = 0

    async def start(self) -> None:
        await self._bot.send_message(self._chat_id, f"{self._title}: начали обработку…")

    async def tick(self, done: int, total: int) -> None:
        if total <= 0:
            return
        percent = int(math.floor((done / total) * 100))
        percent_bucket = percent // 10
        should_send = (done - self._last_sent) >= self._min_step or percent_bucket > self._last_percent_bucket
        if not should_send and done != total:
            return
        self._last_sent = done
        self._last_percent_bucket = percent_bucket
        await self._bot.send_message(
            self._chat_id, f"{self._title}: {done}/{total} ({percent}%)"
        )


@router.callback_query(callbacks.ExportShopAdvExcel.filter())
async def export_shop_adv_excel(
    callback: CallbackQuery,
    callback_data: callbacks.ExportShopAdvExcel,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    # CallbackQuery.from_user в aiogram типизирован как User (не Optional).
    from_user = callback.from_user
    chat_id = callback.message.chat.id
    wb_uc_id = callback_data.wb_user_cabinet_original_id
    try:
        await verify_user_owns_wb_user_cabinet(
            telegram_user_id=from_user.id,
            wb_user_cabinet_id=wb_uc_id,
        )
    except PermissionError:
        await bot.send_message(chat_id, "Нет доступа к этому магазину.")
        return

    await state.update_data(last_wb_user_cabinet_original_id=wb_uc_id)
    progress = _ProgressReporter(
        bot=bot, chat_id=chat_id, title="Выгрузка Excel", min_step=10
    )
    await progress.start()

    try:
        headers, rows = await build_adv_excel_export(
            wb_user_cabinet_id=wb_uc_id,
            progress_callback=progress.tick,
        )

        raw = write_adv_excel_workbook(headers, rows)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        fname = f"adv_campaigns_shop_{stamp}.xlsx"
        await bot.send_document(
            chat_id=chat_id,
            document=BufferedInputFile(raw, fname),
            caption=f"Все активные РК магазина в одном файле: {len(rows)} строк.",
        )
    except Exception:
        logger.exception(
            "adv excel export failed telegram_user_id=%s wb_user_cabinet_id=%s",
            from_user.id,
            wb_uc_id,
        )
        await bot.send_message(
            chat_id,
            "Не удалось сформировать выгрузку Excel. Попробуйте снова чуть позже.",
        )


@router.callback_query(callbacks.ImportShopAdvExcel.filter())
async def import_shop_adv_excel_start(
    callback: CallbackQuery,
    callback_data: callbacks.ImportShopAdvExcel,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None:
        return
    from_user = callback.from_user
    chat_id = callback.message.chat.id
    wb_uc_id = callback_data.wb_user_cabinet_original_id
    try:
        await verify_user_owns_wb_user_cabinet(
            telegram_user_id=from_user.id,
            wb_user_cabinet_id=wb_uc_id,
        )
    except PermissionError:
        await bot.send_message(chat_id, "Нет доступа к этому магазину.")
        return

    await state.set_state(states.AdvExcelRoundtrip.waiting_for_workbook)
    await state.update_data(
        adv_excel_import_wb_user_cabinet_id=int(wb_uc_id),
        adv_excel_from_shop=True,
        last_wb_user_cabinet_original_id=int(wb_uc_id),
    )
    await bot.send_message(
        chat_id,
        "Пришлите файл .xlsx (тот же формат, что и выгрузка «все РК магазина»). "
        "Меняйте только колонки с тех. ключом вида (EDIT__...). "
        "Любая ошибка — файл будет отклонён целиком.",
    )


@router.message(
    StateFilter(states.AdvExcelRoundtrip.waiting_for_workbook),
    F.document,
)
async def import_adv_excel_file(
    message: Message,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if message.from_user is None or message.document is None:
        return
    chat_id = message.chat.id
    doc = message.document
    fname = doc.file_name or ""
    if fname and not fname.lower().endswith(".xlsx"):
        await message.answer("Нужен файл в формате .xlsx")
        return

    buf = io.BytesIO()
    await bot.download(doc, buf)
    content = buf.getvalue()

    data = await state.get_data()
    wb_uc_id = data.get("adv_excel_import_wb_user_cabinet_id")
    if wb_uc_id is None:
        await state.clear()
        await message.answer(
            "Сессия истекла. Откройте меню магазина и снова нажмите «Загрузить настройки из Excel»."
        )
        return

    progress = _ProgressReporter(
        bot=bot, chat_id=chat_id, title="Импорт Excel", min_step=10
    )
    await progress.start()
    _headers, rows = read_adv_excel_upload(content)
    n, max_cpo_decrease_effects = await apply_adv_excel_rows(
        telegram_user_id=message.from_user.id,
        expected_wb_user_cabinet_id=int(wb_uc_id),
        rows=rows,
        progress_callback=progress.tick,
    )

    await state.clear()
    await message.answer(f"Готово. Обновлено кампаний: {n}.")
    for effect in max_cpo_decrease_effects[:10]:
        await message.answer(format_v3_raise_max_auto_disable_message(effect))
    extra = len(max_cpo_decrease_effects) - 10
    if extra > 0:
        await message.answer(
            f"Авто max CPO (V3 Raise) отключено ещё для {extra} РК из-за уменьшения max себестоимости."
        )
    from app.modules.shop_menu.message import ShopMenu

    await ShopMenu(bot, chat_id, state, int(wb_uc_id))()
