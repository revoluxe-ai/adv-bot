"""Read-only seams кнопки AI-пакета: период, shop_id, ZIP, доставка.

Хендлер Telegram не выбирает datasets и не кодирует ZIP. Единственный
export-вызов — ``PackageZipAssembler.assemble_zip``.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date

from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select

from app.client_bot.const import TELEGRAM_CAPTION_LIMIT
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.package_zip_assembler import (
    PackageZipAssembler,
)
from app.modules.common_slaves.wildberries.models import WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.session_maker import get_async_session_maker

ACCESS_DENIED_TEXT = "Нет доступа к этому магазину."
SHOP_UNRESOLVED_TEXT = "Не удалось определить магазин для выгрузки."
EXPORT_FAILED_TEXT = "Не удалось сформировать AI-пакет. Попробуйте позже."
ALREADY_RUNNING_TEXT = "Выгрузка для этого магазина уже формируется."
FORMING_TEXT = "Формирую AI-пакет…"
SIZE_REJECTED_TEXT = (
    "Не удалось отправить AI-пакет: Telegram отклонил файл из-за размера. "
    "Пакет не урезан."
)

_V1_START = date(2026, 9, 21)
_V1_END = date(2026, 10, 4)
_FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_FILENAME_CHARS = 180
_SIZE_MARKERS = (
    "file is too big",
    "request entity too large",
    "entity too large",
    "file too large",
    "too big",
)


def v1_shop_menu_export_period() -> ExportPeriod:
    """Период кнопки V1: фиксированное окно acceptance.

    Единственное место выбора дат для меню. Следующая фича может подставить
    custom dates, стандартный горизонт или последний полный период, не меняя
    ``PackageZipAssembler``.

    Returns:
        Канонический ``ExportPeriod`` 2026-09-21..2026-10-04 включительно.
    """
    return ExportPeriod(start=_V1_START, end=_V1_END)


async def resolve_canonical_shop_id(wb_user_cabinet_id: int) -> str | None:
    """Резолв ``WBCabinet.shop_id`` по ``WBUserCabinet.id``.

    Только read-only PostgreSQL SELECT. Имя магазина и текст callback не
    используются. Пустой или отсутствующий mapping → ``None`` (fail closed).

    Args:
        wb_user_cabinet_id: Первичный ключ ``WBUserCabinet``, уже прошедший
            проверку владельца.

    Returns:
        Канонический ``shop_id`` или ``None``.
    """
    async with get_async_session_maker(read_only=True) as session:
        stmt = (
            select(WBCabinet.shop_id)
            .join(WBUserCabinet, WBUserCabinet.wb_cabinet_id == WBCabinet.id)
            .where(WBUserCabinet.id == wb_user_cabinet_id)
        )
        value = (await session.execute(stmt)).scalar_one_or_none()
    if value is None:
        return None
    shop_id = str(value).strip()
    if not shop_id:
        return None
    return shop_id


async def assemble_shop_package(shop_id: str, period: ExportPeriod) -> bytes:
    """Собрать ZIP через канонический assembler.

    Args:
        shop_id: ``WBCabinet.shop_id``, не id кабинета.
        period: Период из ``v1_shop_menu_export_period`` или будущего seam.

    Returns:
        Байты ZIP без записи на локальный диск.
    """
    assembler = PackageZipAssembler()
    return await assembler.assemble_zip(shop_id, period)


def build_ai_package_filename(shop_id: str, period: ExportPeriod) -> str:
    """Детерминированное имя ZIP без секретов и внутренних id.

    Args:
        shop_id: Канонический shop id (санитизируется).
        period: Период, который попадёт в имя файла.

    Returns:
        Имя вида ``WB_SKY_AI_PACKAGE_<shop>_YYYY-MM-DD_YYYY-MM-DD.zip``.
    """
    dates = f"{period.start.isoformat()}_{period.end.isoformat()}"
    safe = _FILENAME_UNSAFE.sub("_", shop_id).strip("._") or "shop"
    suffix = f"_{dates}.zip"
    prefix = "WB_SKY_AI_PACKAGE_"
    budget = _MAX_FILENAME_CHARS - len(prefix) - len(suffix)
    if budget < 1:
        budget = 1
    if len(safe) > budget:
        safe = safe[:budget].rstrip("._") or "shop"
    return f"{prefix}{safe}{suffix}"


def build_ai_package_caption(shop_id: str, period: ExportPeriod) -> str:
    """Подпись документа: магазин, период, успешная сборка.

    Длинный ``shop_id`` обрезается так, чтобы длина не превысила
    ``TELEGRAM_CAPTION_LIMIT``. Внутренние id БД и токены не включаются.

    Args:
        shop_id: Канонический shop id для человека.
        period: Период выгрузки.

    Returns:
        Текст caption в пределах лимита Telegram.
    """
    tail = f"\nПериод: {period.start.isoformat()} — {period.end.isoformat()}"
    head = "AI-пакет сформирован.\nМагазин: "
    room = TELEGRAM_CAPTION_LIMIT - len(head) - len(tail)
    shown = shop_id
    if room < 1:
        shown = ""
    elif len(shown) > room:
        if room == 1:
            shown = "…"
        else:
            shown = shown[: room - 1] + "…"
    caption = f"{head}{shown}{tail}"
    if len(caption) > TELEGRAM_CAPTION_LIMIT:
        caption = caption[:TELEGRAM_CAPTION_LIMIT]
    return caption


def is_telegram_file_too_large(exc: BaseException) -> bool:
    """True, если Telegram отклонил документ из-за размера.

    Лимит байт ZIP здесь не зашит: решение принимает ответ API.

    Args:
        exc: Исключение ``send_document``.

    Returns:
        Признак отказа по размеру.
    """
    if not isinstance(exc, TelegramBadRequest):
        return False
    raw = getattr(exc, "message", None)
    text = (raw if isinstance(raw, str) else str(exc)).lower()
    return any(marker in text for marker in _SIZE_MARKERS)


class ExportInflightGuard:
    """In-process lock на пару telegram user + WBUserCabinet.

    Не общий Redis и не очередь заданий. Второй клик в том же процессе не
    стартует второй ``assemble_zip``. Другие реплики бота этот lock не видят.
    """

    def __init__(self) -> None:
        self._guard = asyncio.Lock()
        self._locks: dict[tuple[int, int], asyncio.Lock] = {}

    async def try_acquire(
        self, telegram_user_id: int, wb_user_cabinet_id: int
    ) -> asyncio.Lock | None:
        """Захватить lock или вернуть ``None``, если выгрузка уже идёт.

        Args:
            telegram_user_id: ``callback.from_user.id``.
            wb_user_cabinet_id: id кабинета из callback.

        Returns:
            Удерживаемый ``asyncio.Lock`` либо ``None``.
        """
        key = (telegram_user_id, wb_user_cabinet_id)
        async with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            if lock.locked():
                return None
            await lock.acquire()
            return lock


_INFLIGHT = ExportInflightGuard()


def inflight_guard() -> ExportInflightGuard:
    """Процессный guard повторных кликов кнопки AI-пакета."""
    return _INFLIGHT
