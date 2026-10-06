"""Unit-тесты transport-кнопки AI-пакета (spec telegram-ai-package-export).

Проверяют клавиатуру, авторизацию, shop_id, период, канонический assembler,
сообщения об ошибках, повторный клик и отсутствие write-адаптеров. Реальные
PG/CH/WB не вызываются.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramBadRequest

from app.client_bot.const import TELEGRAM_CAPTION_LIMIT, TELEGRAM_TEXT_MESSAGE_LIMIT
from app.client_bot.ui_access import UiAccessMode
from app.client_bot.user_interface.handlers.shop_ai_package_export import (
    export_shop_ai_package,
)
from app.client_bot.user_interface.services.shop_ai_package_export.flow import (
    ACCESS_DENIED_TEXT,
    ALREADY_RUNNING_TEXT,
    EXPORT_FAILED_TEXT,
    FORMING_TEXT,
    SHOP_UNRESOLVED_TEXT,
    SIZE_REJECTED_TEXT,
    assemble_shop_package,
    build_ai_package_caption,
    build_ai_package_filename,
    is_telegram_file_too_large,
    resolve_canonical_shop_id,
    v1_shop_menu_export_period,
)
from app.client_bot.user_interface.views.callbacks import (
    ExportShopAdvExcel,
    ExportShopAiPackage,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.shop_menu.message import build_shop_main_keyboard
from tests.helpers.telegram_message_asserts import (
    assert_caption_within_telegram_limit,
    assert_keyboard_has_buttons,
    assert_message_within_telegram_limit,
    assert_no_raw_technical_text,
)

pytestmark = pytest.mark.unit

_REPO = Path(__file__).resolve().parents[3]
_HANDLER = (
    _REPO
    / "app/client_bot/user_interface/handlers/shop_ai_package_export.py"
)
_FLOW = (
    _REPO
    / "app/client_bot/user_interface/services/shop_ai_package_export/flow.py"
)
_FORBIDDEN_SNIPPETS = (
    "WBShopDataManager",
    "get_clickhouse_client",
    "ApplyManager",
    "session.commit",
    "session.add(",
    "subprocess",
    "C:\\Users",
    "scripts/ai_package",
)


def _keyboard(cabinet_id: int, mode: UiAccessMode):
    """Клавиатура магазина с заданным WBUserCabinet.id."""
    user_cabinet = MagicMock()
    user_cabinet.id = cabinet_id
    user_cabinet.user = None
    cabinet = MagicMock()
    cabinet.id = 1
    cabinet.active = True
    return build_shop_main_keyboard(user_cabinet, cabinet, ui_access=mode)


def _callback(user_id: int, cabinet_id: int):
    """CallbackQuery и bot-заглушки без сети Telegram."""
    callback = MagicMock()
    callback.from_user.id = user_id
    callback.message.chat.id = 501
    callback_data = ExportShopAiPackage(wb_user_cabinet_original_id=cabinet_id)
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_document = AsyncMock()
    return callback, callback_data, bot


def _too_big_error() -> TelegramBadRequest:
    """TelegramBadRequest с текстом отказа по размеру, без реального method."""
    exc = TelegramBadRequest.__new__(TelegramBadRequest)
    exc.message = "Bad Request: file is too big"
    return exc


def _texts(bot: MagicMock) -> list[str]:
    """Тексты send_message в порядке вызовов."""
    return [call.args[1] for call in bot.send_message.await_args_list]


@pytest.mark.unit
def test_shop_menu_ai_package_button_carries_cabinet_id() -> None:
    """Кнопка есть в FREE и PAID, callback хранит только id кабинета."""
    for mode in (UiAccessMode.FREE, UiAccessMode.PAID):
        keyboard = _keyboard(4242, mode)
        assert_keyboard_has_buttons(keyboard, ["📦 Выгрузить AI-пакет"])
        packed = [
            button.callback_data
            for row in keyboard.inline_keyboard
            for button in row
            if button.text == "📦 Выгрузить AI-пакет"
        ]
        assert len(packed) == 1
        raw = packed[0]
        assert raw is not None
        assert 1 <= len(raw.encode("utf-8")) <= 64
        parsed = ExportShopAiPackage.unpack(raw)
        assert parsed.wb_user_cabinet_original_id == 4242
        excel = ExportShopAdvExcel(wb_user_cabinet_original_id=4242).pack()
        assert raw != excel


@pytest.mark.unit
def test_ai_package_callback_worst_case_fits_64_bytes() -> None:
    """callback_data измеряется в байтах UTF-8 и не содержит shop UUID."""
    packed = ExportShopAiPackage(
        wb_user_cabinet_original_id=2_147_483_647
    ).pack()
    assert len(packed.encode("utf-8")) <= 64
    assert "shop_id" not in packed
    for text in (
        ACCESS_DENIED_TEXT,
        SHOP_UNRESOLVED_TEXT,
        EXPORT_FAILED_TEXT,
        ALREADY_RUNNING_TEXT,
        FORMING_TEXT,
        SIZE_REJECTED_TEXT,
    ):
        assert len(text) <= TELEGRAM_TEXT_MESSAGE_LIMIT
        assert_message_within_telegram_limit(text)
        assert_no_raw_technical_text(text)


@pytest.mark.unit
def test_v1_period_is_canonical_acceptance_window() -> None:
    """Период кнопки — ровно 2026-09-21..2026-10-04 через ExportPeriod."""
    period = v1_shop_menu_export_period()
    assert isinstance(period, ExportPeriod)
    assert period.start == date(2026, 9, 21)
    assert period.end == date(2026, 10, 4)


@pytest.mark.unit
def test_caption_and_filename_stay_within_limits() -> None:
    """Длинный shop_id не раздувает caption; имя файла заканчивается на .zip."""
    period = v1_shop_menu_export_period()
    shop_id = "магазин_" + ("Ж" * 4000) + "<>&"
    caption = build_ai_package_caption(shop_id, period)
    assert_caption_within_telegram_limit(caption)
    assert len(caption) <= TELEGRAM_CAPTION_LIMIT
    assert "AI-пакет сформирован." in caption
    assert "2026-09-21" in caption
    assert "2026-10-04" in caption
    assert_no_raw_technical_text(caption)
    filename = build_ai_package_filename(shop_id, period)
    assert filename.endswith(".zip")
    assert filename.startswith("WB_SKY_AI_PACKAGE_")
    assert "2026-09-21_2026-10-04" in filename
    assert len(filename) <= 180
    assert "<" not in filename


@pytest.mark.asyncio
async def test_assemble_uses_package_zip_assembler_only() -> None:
    """Seam вызывает PackageZipAssembler.assemble_zip и возвращает его bytes."""
    period = v1_shop_menu_export_period()
    assembler = MagicMock()
    assembler.assemble_zip = AsyncMock(return_value=b"PK\x03\x04zip")
    with patch(
        "app.client_bot.user_interface.services.shop_ai_package_export.flow."
        "PackageZipAssembler",
        return_value=assembler,
    ) as ctor:
        payload = await assemble_shop_package("shop-77", period)
    ctor.assert_called_once_with()
    assembler.assemble_zip.assert_awaited_once_with("shop-77", period)
    assert payload == b"PK\x03\x04zip"


@pytest.mark.asyncio
async def test_resolve_shop_id_reads_canonical_column() -> None:
    """SELECT возвращает WBCabinet.shop_id; пустой mapping fail-closed."""
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = "  shop-abc  "
    session.execute = AsyncMock(return_value=result)

    class _Ctx:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *_exc: object) -> bool:
            return False

    def _maker(read_only: bool = False):
        assert read_only is True
        return _Ctx()

    with patch(
        "app.client_bot.user_interface.services.shop_ai_package_export.flow."
        "get_async_session_maker",
        side_effect=_maker,
    ):
        shop_id = await resolve_canonical_shop_id(15)
    assert shop_id == "shop-abc"
    session.commit.assert_not_called()
    result.scalar_one_or_none.return_value = "   "
    with patch(
        "app.client_bot.user_interface.services.shop_ai_package_export.flow."
        "get_async_session_maker",
        side_effect=_maker,
    ):
        missing = await resolve_canonical_shop_id(15)
    assert missing is None


@pytest.mark.asyncio
async def test_authorized_export_sends_zip_document() -> None:
    """Авторизованный пользователь получает ZIP с именем .zip и периодом."""
    callback, data, bot = _callback(7, 11)
    period = v1_shop_menu_export_period()
    with (
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "verify_user_owns_wb_user_cabinet",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "resolve_canonical_shop_id",
            new=AsyncMock(return_value="shop-77"),
        ) as resolve,
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "assemble_shop_package",
            new=AsyncMock(return_value=b"PK\x03\x04"),
        ) as assemble,
    ):
        await export_shop_ai_package(callback, data, bot)
    resolve.assert_awaited_once_with(11)
    assemble.assert_awaited_once()
    awaited = assemble.await_args
    assert awaited is not None
    assert awaited.args[0] == "shop-77"
    assert awaited.args[1] == period
    assert _texts(bot)[0] == FORMING_TEXT
    bot.send_document.assert_awaited_once()
    kwargs = bot.send_document.await_args.kwargs
    document = kwargs["document"]
    assert document.filename.endswith(".zip")
    assert document.filename.startswith("WB_SKY_AI_PACKAGE_shop-77_")
    assert kwargs["caption"]
    assert "shop-77" in kwargs["caption"]
    assert "2026-09-21" in kwargs["caption"]


@pytest.mark.asyncio
async def test_foreign_user_does_not_call_exporter() -> None:
    """Чужой пользователь получает отказ, assembler и shop resolve не зовутся."""
    callback, data, bot = _callback(8, 11)
    with (
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "verify_user_owns_wb_user_cabinet",
            new=AsyncMock(side_effect=PermissionError("secret-token")),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "resolve_canonical_shop_id",
            new=AsyncMock(),
        ) as resolve,
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "assemble_shop_package",
            new=AsyncMock(),
        ) as assemble,
    ):
        await export_shop_ai_package(callback, data, bot)
    resolve.assert_not_awaited()
    assemble.assert_not_awaited()
    assert _texts(bot) == [ACCESS_DENIED_TEXT]
    assert "secret-token" not in _texts(bot)[0]


@pytest.mark.asyncio
async def test_missing_shop_mapping_fails_closed() -> None:
    """Сломанный mapping не вызывает assembler."""
    callback, data, bot = _callback(7, 11)
    with (
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "verify_user_owns_wb_user_cabinet",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "resolve_canonical_shop_id",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "assemble_shop_package",
            new=AsyncMock(),
        ) as assemble,
    ):
        await export_shop_ai_package(callback, data, bot)
    assemble.assert_not_awaited()
    assert SHOP_UNRESOLVED_TEXT in _texts(bot)


@pytest.mark.asyncio
async def test_assembler_exception_is_safe_for_user() -> None:
    """Исключение assembler не попадает в текст пользователю."""
    callback, data, bot = _callback(7, 11)
    with (
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "verify_user_owns_wb_user_cabinet",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "resolve_canonical_shop_id",
            new=AsyncMock(return_value="shop-77"),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "assemble_shop_package",
            new=AsyncMock(side_effect=RuntimeError("wb_token=SUPERSECRET")),
        ),
    ):
        await export_shop_ai_package(callback, data, bot)
    joined = "\n".join(_texts(bot))
    assert EXPORT_FAILED_TEXT in joined
    assert "SUPERSECRET" not in joined
    assert "RuntimeError" not in joined
    bot.send_document.assert_not_awaited()


@pytest.mark.asyncio
async def test_telegram_size_rejection_does_not_truncate() -> None:
    """Отказ Telegram по размеру даёт явный текст и не шлёт урезанный ZIP."""
    callback, data, bot = _callback(7, 11)
    bot.send_document = AsyncMock(side_effect=_too_big_error())
    assert is_telegram_file_too_large(_too_big_error())
    with (
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "verify_user_owns_wb_user_cabinet",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "resolve_canonical_shop_id",
            new=AsyncMock(return_value="shop-77"),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "assemble_shop_package",
            new=AsyncMock(return_value=b"PK-full-not-stripped"),
        ) as assemble,
    ):
        await export_shop_ai_package(callback, data, bot)
    assemble.assert_awaited_once()
    assert SIZE_REJECTED_TEXT in _texts(bot)
    assert bot.send_document.await_count == 1


@pytest.mark.asyncio
async def test_duplicate_click_runs_one_export() -> None:
    """Пока первая выгрузка идёт, второй клик не вызывает assembler снова."""
    callback, data, bot = _callback(70, 110)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = {"n": 0}

    async def _slow(shop_id: str, period: ExportPeriod) -> bytes:
        calls["n"] += 1
        started.set()
        await release.wait()
        assert shop_id == "shop-77"
        assert period.start == date(2026, 9, 21)
        return b"PK"

    with (
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "verify_user_owns_wb_user_cabinet",
            new=AsyncMock(return_value=MagicMock()),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "resolve_canonical_shop_id",
            new=AsyncMock(return_value="shop-77"),
        ),
        patch(
            "app.client_bot.user_interface.handlers.shop_ai_package_export."
            "assemble_shop_package",
            new=_slow,
        ),
    ):
        first = asyncio.create_task(export_shop_ai_package(callback, data, bot))
        await started.wait()
        await export_shop_ai_package(callback, data, bot)
        release.set()
        await first
    assert calls["n"] == 1
    assert ALREADY_RUNNING_TEXT in _texts(bot)


@pytest.mark.unit
def test_transport_sources_have_no_write_adapters() -> None:
    """Хендлер и flow не импортируют WB/CH/PG writers и локальные скрипты."""
    handler_src = _HANDLER.read_text(encoding="utf-8")
    flow_src = _FLOW.read_text(encoding="utf-8")
    combined = handler_src + "\n" + flow_src
    for snippet in _FORBIDDEN_SNIPPETS:
        assert snippet not in combined
    assert "PackageZipAssembler" in flow_src
    assert "assemble_zip" in flow_src
    assert "read_only=True" in flow_src
    assert "def export_shop_ai_package" in handler_src
    assert inspect.iscoroutinefunction(export_shop_ai_package)
