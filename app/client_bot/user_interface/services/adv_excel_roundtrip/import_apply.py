"""Валидация и применение загруженного Excel."""

from __future__ import annotations

import math
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EXCEL_TEMPLATE_VERSION,
    column_header,
    edit_header,
    parse_edit_value,
    technical_column_header,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EDITABLE_ADV_SETTING_COLUMNS,
)
from app.client_bot import const
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

_sm = get_async_session_maker
ProgressCallback = Callable[[int, int], Awaitable[None] | None]


async def _telegram_may_access_wb_user_cabinet(
    session: Any, *, telegram_user_id: int, wuc: WBUserCabinet
) -> bool:
    """Доступ как у меню магазина: владелец связки или админ (см. get_shop_for_admin)."""
    if telegram_user_id in const.ADMINS:
        return True
    stmt = select(User.id).where(
        User.id == wuc.user_id,
        User.user_telegram_id == telegram_user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def verify_user_owns_wb_user_cabinet(
    *, telegram_user_id: int, wb_user_cabinet_id: int
) -> WBUserCabinet:
    """Проверка доступа к WBUserCabinet (владелец или админ).

    Читаем с primary (read_only=False): на реплике возможен лаг, из‑за него
    валидный доступ ошибочно отклонялся.

    Ошибку доступа выбрасываем уже после закрытия сессии, чтобы обёртка
    session_maker не логировала её как «Session error».
    """
    wuc: WBUserCabinet | None = None
    async with _sm(read_only=False) as session:
        row = await session.get(WBUserCabinet, wb_user_cabinet_id)
        if row is not None and await _telegram_may_access_wb_user_cabinet(
            session, telegram_user_id=telegram_user_id, wuc=row
        ):
            wuc = row
    if wuc is None:
        raise PermissionError("Нет доступа к этому магазину")
    return wuc


def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and (math.isnan(v) or str(v) == "nan"):
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def _coerce_int(v: Any) -> int | None:
    if _is_blank(v):
        return None
    if isinstance(v, bool):
        raise ValueError(f"Ожидалось число, получено bool: {v}")
    return int(float(v))


def _same_optional_int(a: int | None, b: int | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return int(a) == int(b)


def _is_active_adv(a: AdvSetting) -> bool:
    return bool(a.active_status and a.bot_active)


def _row_value(
    row: dict[str, Any], *, kind: str, field: str, suffix: str = ""
) -> Any:
    ui_h = column_header(kind, field, suffix)
    if ui_h in row:
        return row[ui_h]
    tech_h = technical_column_header(kind, field, suffix)
    return row.get(tech_h)


class AdvExcelImportError(Exception):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("\n".join(messages))


async def apply_adv_excel_rows(
    *,
    telegram_user_id: int,
    expected_wb_user_cabinet_id: int,
    rows: list[dict[str, Any]],
    progress_callback: ProgressCallback | None = None,
) -> int:
    """Применить строки Excel. Возвращает число обновлённых РК. Любая ошибка — исключение."""
    if not rows:
        raise AdvExcelImportError(["Файл не содержит строк с данными"])

    tpl_col = column_header("RO", "excel_template_version")
    v0 = _row_value(rows[0], kind="RO", field="excel_template_version")
    if _is_blank(v0):
        raise AdvExcelImportError([f"Нет колонки или значения {tpl_col}"])
    try:
        tv = int(float(v0))
    except (TypeError, ValueError) as e:
        raise AdvExcelImportError([f"Неверная версия шаблона: {v0!r}"]) from e
    if tv != EXCEL_TEMPLATE_VERSION:
        raise AdvExcelImportError(
            [f"Версия шаблона {tv}, ожидается {EXCEL_TEMPLATE_VERSION}"]
        )

    updated = 0
    async with _sm(read_only=False) as session:
        wuc_check = await session.get(WBUserCabinet, expected_wb_user_cabinet_id)
        if not wuc_check:
            raise AdvExcelImportError(["Сессия магазина не найдена"])
        if not await _telegram_may_access_wb_user_cabinet(
            session, telegram_user_id=telegram_user_id, wuc=wuc_check
        ):
            raise AdvExcelImportError(["Нет доступа к этому магазину"])

        total = len(rows)
        for i, row in enumerate(rows, start=1):
            aid = _coerce_int(_row_value(row, kind="RO", field="adv_setting_id"))
            if aid is None:
                raise AdvExcelImportError([f"Строка {i}: нет RO__adv_setting_id"])

            adv = await session.get(
                AdvSetting,
                aid,
                options=[joinedload(AdvSetting.wb_cabinet)],
            )
            if not adv:
                raise AdvExcelImportError([f"Строка {i}: РК id={aid} не найдена"])

            if adv.wb_cabinet_id != wuc_check.wb_cabinet_id:
                raise AdvExcelImportError(
                    [f"Строка {i}: РК не относится к выбранному магазину"]
                )

            if not _is_active_adv(adv):
                raise AdvExcelImportError(
                    [f"Строка {i}: РК не активна (нужны active_status и bot_active)"]
                )

            ro_adv = _coerce_int(_row_value(row, kind="RO", field="adv_id"))
            ro_search = _coerce_int(_row_value(row, kind="RO", field="search_adv_id"))
            ro_nmid = _coerce_int(_row_value(row, kind="RO", field="nmid"))

            if not _same_optional_int(ro_adv, adv.adv_id):
                raise AdvExcelImportError(
                    [f"Строка {i}: RO__adv_id не совпадает с данными сервера"]
                )
            if not _same_optional_int(ro_search, adv.search_adv_id):
                raise AdvExcelImportError(
                    [f"Строка {i}: RO__search_adv_id не совпадает с данными сервера"]
                )
            first_nmid = int(adv.nmids[0]) if adv.nmids else None
            if not _same_optional_int(ro_nmid, first_nmid):
                raise AdvExcelImportError(
                    [f"Строка {i}: RO__nmid не совпадает с данными сервера"]
                )

            for field in sorted(EDITABLE_ADV_SETTING_COLUMNS):
                h = edit_header(field)
                if h not in row:
                    continue
                raw = row[h]
                if _is_blank(raw):
                    continue
                try:
                    val = parse_edit_value(field, raw)
                except ValueError as e:
                    raise AdvExcelImportError(
                        [f"Строка {i}, колонка {h}: {e}"]
                    ) from e
                if field in {
                    "plan_for_sales_for_day",
                    "target_price_for_order",
                    "max_price_for_order",
                } and float(val) < 1:
                    raise AdvExcelImportError(
                        [f"Строка {i}, колонка {h}: значение должно быть >= 1"]
                    )
                setattr(adv, field, val)

            updated += 1
            if progress_callback is not None:
                awaitable = progress_callback(i, total)
                if awaitable is not None:
                    await awaitable

        await session.commit()

    return updated
