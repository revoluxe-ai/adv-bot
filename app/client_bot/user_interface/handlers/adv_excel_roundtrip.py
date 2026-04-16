"""Excel: выгрузка / загрузка настроек активных РК по магазину (меню магазина)."""

from __future__ import annotations

import io
import logging
from datetime import datetime

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
    AdvExcelImportError,
    apply_adv_excel_rows,
    verify_user_owns_wb_user_cabinet,
)
from app.client_bot.user_interface.views import callbacks

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(callbacks.ExportShopAdvExcel.filter())
async def export_shop_adv_excel(
    callback: CallbackQuery,
    callback_data: callbacks.ExportShopAdvExcel,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None or callback.from_user is None:
        return
    await callback.answer()
    chat_id = callback.message.chat.id
    wb_uc_id = callback_data.wb_user_cabinet_original_id
    try:
        await verify_user_owns_wb_user_cabinet(
            telegram_user_id=callback.from_user.id,
            wb_user_cabinet_id=wb_uc_id,
        )
    except PermissionError:
        await bot.send_message(chat_id, "Нет доступа к этому магазину.")
        return

    await state.update_data(last_wb_user_cabinet_original_id=wb_uc_id)

    try:
        headers, rows = await build_adv_excel_export(wb_user_cabinet_id=wb_uc_id)
    except Exception:
        logger.exception("export_shop_adv_excel failed wb_uc_id=%s", wb_uc_id)
        await bot.send_message(
            chat_id, "Ошибка при формировании выгрузки. Попробуйте позже."
        )
        return

    raw = write_adv_excel_workbook(headers, rows)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    fname = f"adv_campaigns_shop_{stamp}.xlsx"
    await bot.send_document(
        chat_id=chat_id,
        document=BufferedInputFile(raw, fname),
        caption=f"Все активные РК магазина в одном файле: {len(rows)} строк.",
    )


@router.callback_query(callbacks.ImportShopAdvExcel.filter())
async def import_shop_adv_excel_start(
    callback: CallbackQuery,
    callback_data: callbacks.ImportShopAdvExcel,
    bot: aiogram.Bot,
    state: FSMContext,
) -> None:
    if callback.message is None or callback.from_user is None:
        return
    await callback.answer()
    chat_id = callback.message.chat.id
    wb_uc_id = callback_data.wb_user_cabinet_original_id
    try:
        await verify_user_owns_wb_user_cabinet(
            telegram_user_id=callback.from_user.id,
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
        "Меняйте только колонки EDIT__*. Любая ошибка — файл будет отклонён целиком.",
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

    try:
        _headers, rows = read_adv_excel_upload(content)
        n = await apply_adv_excel_rows(
            telegram_user_id=message.from_user.id,
            expected_wb_user_cabinet_id=int(wb_uc_id),
            rows=rows,
        )
    except AdvExcelImportError as e:
        text = "Импорт отклонён:\n" + "\n".join(f"• {m}" for m in e.messages[:50])
        if len(e.messages) > 50:
            text += f"\n… и ещё {len(e.messages) - 50} ошибок"
        await message.answer(text)
        return
    except Exception:
        logger.exception("import_adv_excel_file failed")
        await state.clear()
        await message.answer(
            "Ошибка при разборе файла. Проверьте формат и попробуйте снова."
        )
        return

    await state.clear()
    await message.answer(f"Готово. Обновлено кампаний: {n}.")
    from app.modules.shop_menu.message import ShopMenu

    await ShopMenu(bot, chat_id, state, int(wb_uc_id))()
