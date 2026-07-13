"""Валидация и применение загруженного Excel.

Архитектурное решение по ошибкам импорта:
- Любая ошибка валидации/применения поднимается как исключение и НЕ обрабатывается
  локально в handler импорта.
- Ответ пользователю формируется единообразно в глобальном error-handler'е
  (`app.client_bot.user_interface.handlers.exceptions`): без детальных причин.
- Детали причины (строка/колонка/значение) остаются в тексте исключения для
  логов и уведомления администратора, но не являются user-facing контрактом.

Таким образом импорт придерживается политики "fail-fast + единый UX ошибок":
файл отклоняется целиком, а диагностика уходит в технический контур.
"""

from __future__ import annotations

import math
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.client_bot.user_interface.services.adv_excel_roundtrip.active_adv import (
    is_active_adv,
)
from app.client_bot.user_interface.services.adv_excel_roundtrip.schema import (
    EDITABLE_ADV_SETTING_COLUMNS,
    EDITABLE_SHELF_BID_CONTROL_COLUMNS,
    EXCEL_TEMPLATE_VERSION,
    ExcelColumnKind,
    column_header,
    edit_header,
    header_type_suffix,
    parse_edit_value,
    technical_column_header,
)
from app.client_bot import const
from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.auto_shelf_bid_control import (
    AutoShelfBidControlSettings,
)
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

from app.modules.sales_plan_settings.v3_raise_max_cpo import (
    MaxCpoDecreaseSideEffect,
    resolve_flag_after_max_cpo_decrease,
    skip_excel_substitute_fact_cpo_for_max,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    normalize_card_ab_hold_mode,
)
from app.modules.shop_runner.service_manager.services.auto_shelf_bid_control_manager.auto_shelf_bid_control_repository import (
    DEFAULT_CURRENCY,
    DEFAULT_MAX_BID_MINOR,
    DEFAULT_MIN_BID_DISTANCE_MINOR,
    DEFAULT_TARGET_TEST_IMPRESSIONS,
    DEFAULT_TARGET_TEST_OBSERVATION_MINUTES,
    DEFAULT_TEST_SHARE,
)

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


def _row_value(
    row: dict[str, Any], *, kind: ExcelColumnKind, field: str, suffix: str = ""
) -> Any:
    ui_h = column_header(kind, field, suffix)
    if ui_h in row:
        return row[ui_h]
    tech_h = technical_column_header(kind, field, suffix)
    return row.get(tech_h)


def _row_has_non_blank_shelf_value(row: dict[str, Any]) -> bool:
    for field in EDITABLE_SHELF_BID_CONTROL_COLUMNS:
        if not _is_blank(
            _row_value(
                row,
                kind="EDIT",
                field=field,
                suffix=header_type_suffix(field),
            )
        ):
            return True
    return False


async def _get_or_create_default_shelf_settings(
    session: Any, *, nmid: int
) -> AutoShelfBidControlSettings:
    """Вернуть shelf-настройки по nmid, создавая строку с product-дефолтами."""
    stmt = select(AutoShelfBidControlSettings).where(
        AutoShelfBidControlSettings.nmid == nmid
    )
    settings = (await session.execute(stmt)).scalar_one_or_none()
    if settings is not None:
        return settings
    settings = AutoShelfBidControlSettings(
        nmid=nmid,
        max_bid_minor=DEFAULT_MAX_BID_MINOR,
        currency=DEFAULT_CURRENCY,
        min_bid_distance_minor=DEFAULT_MIN_BID_DISTANCE_MINOR,
        target_test_impressions=DEFAULT_TARGET_TEST_IMPRESSIONS,
        target_test_observation_minutes=DEFAULT_TARGET_TEST_OBSERVATION_MINUTES,
        test_share=DEFAULT_TEST_SHARE,
    )
    session.add(settings)
    await session.flush()
    return settings


class AdvExcelImportError(Exception):
    """Техническая ошибка импорта Excel.

    ВАЖНО: это НЕ user-facing исключение.
    Его текст предназначен для логов/админ-диагностики в общем error-handler'е,
    а пользователь получает стандартное общее сообщение об ошибке интерфейса.
    """


async def apply_adv_excel_rows(
    *,
    telegram_user_id: int,
    expected_wb_user_cabinet_id: int,
    rows: list[dict[str, Any]],
    progress_callback: ProgressCallback | None = None,
) -> tuple[int, list[MaxCpoDecreaseSideEffect]]:
    """Применить строки Excel и вернуть число обновлённых РК и side-effects V3 Raise MAX.

    Контракт по ошибкам:
    - при любой проблеме выбрасывается `AdvExcelImportError`;
    - исключение специально пробрасывается вверх до общего error-handler'а;
    - локально здесь ошибки не "очеловечиваются" для пользователя.
    """
    if not rows:
        raise AdvExcelImportError("Файл не содержит строк с данными")

    tpl_col = column_header("RO", "excel_template_version")
    v0 = _row_value(rows[0], kind="RO", field="excel_template_version")
    if _is_blank(v0):
        raise AdvExcelImportError(f"Нет колонки или значения {tpl_col}")
    try:
        tv = int(float(v0))
    except (TypeError, ValueError) as e:
        raise AdvExcelImportError(f"Неверная версия шаблона: {v0!r}") from e
    if tv != EXCEL_TEMPLATE_VERSION:
        raise AdvExcelImportError(
            f"Версия шаблона {tv}, ожидается {EXCEL_TEMPLATE_VERSION}"
        )

    updated = 0
    max_cpo_decrease_effects: list[MaxCpoDecreaseSideEffect] = []
    async with _sm(read_only=False) as session:
        wuc_check = await session.get(WBUserCabinet, expected_wb_user_cabinet_id)
        if not wuc_check:
            raise AdvExcelImportError("Сессия магазина не найдена")
        if not await _telegram_may_access_wb_user_cabinet(
            session, telegram_user_id=telegram_user_id, wuc=wuc_check
        ):
            raise AdvExcelImportError("Нет доступа к этому магазину")

        total = len(rows)
        for i, row in enumerate(rows, start=1):
            aid = _coerce_int(_row_value(row, kind="RO", field="adv_setting_id"))
            if aid is None:
                raise AdvExcelImportError(f"Строка {i}: нет RO__adv_setting_id")

            adv = await session.get(
                AdvSetting,
                aid,
                options=[joinedload(AdvSetting.wb_cabinet)],
            )
            if not adv:
                raise AdvExcelImportError(f"Строка {i}: РК id={aid} не найдена")

            if adv.wb_cabinet_id != wuc_check.wb_cabinet_id:
                raise AdvExcelImportError(
                    f"Строка {i}: РК не относится к выбранному магазину"
                )

            if not is_active_adv(adv):
                raise AdvExcelImportError(
                    f"Строка {i}: РК не активна (нужны active_status и bot_active)"
                )

            ro_adv = _coerce_int(_row_value(row, kind="RO", field="adv_id"))
            ro_search = _coerce_int(_row_value(row, kind="RO", field="search_adv_id"))
            ro_nmid = _coerce_int(_row_value(row, kind="RO", field="nmid"))

            if not _same_optional_int(ro_adv, adv.adv_id):
                raise AdvExcelImportError(
                    f"Строка {i}: RO__adv_id не совпадает с данными сервера"
                )
            if not _same_optional_int(ro_search, adv.search_adv_id):
                raise AdvExcelImportError(
                    f"Строка {i}: RO__search_adv_id не совпадает с данными сервера"
                )
            first_nmid = int(adv.nmids[0]) if adv.nmids else None
            if not _same_optional_int(ro_nmid, first_nmid):
                raise AdvExcelImportError(
                    f"Строка {i}: RO__nmid не совпадает с данными сервера"
                )

            raise_max_auto_disabled = False
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
                    raise AdvExcelImportError(f"Строка {i}, колонка {h}: {e}") from e
                if field in {
                    "plan_for_sales_for_day",
                    "target_price_for_order",
                    "max_price_for_order",
                } and float(val) < 1:
                    raise AdvExcelImportError(
                        f"Строка {i}, колонка {h}: значение должно быть >= 1"
                    )
                if field == "max_price_for_order":
                    old_max = adv.max_price_for_order
                    new_max = int(val)
                    new_flag, side_effect = resolve_flag_after_max_cpo_decrease(
                        old_max=old_max,
                        new_max=new_max,
                        current_flag=bool(adv.substitute_fact_cpo_for_max),
                        adv_id=int(adv.adv_id),
                    )
                    setattr(adv, field, new_max)
                    adv.substitute_fact_cpo_for_max = new_flag
                    if side_effect is not None:
                        max_cpo_decrease_effects.append(side_effect)
                        raise_max_auto_disabled = True
                    continue
                if field == "card_ab_hold_mode":
                    mode = normalize_card_ab_hold_mode(str(val))
                    if mode != CardAbHoldMode.OFF and not bool(adv.bot_active):
                        raise AdvExcelImportError(
                            f"Строка {i}, колонка {h}: A/B Hold только при bot_active=True "
                            "(spec card-ab-hold-mode)"
                        )
                    setattr(adv, field, mode.value)
                    continue
                if skip_excel_substitute_fact_cpo_for_max(
                    field=field,
                    raise_max_auto_disabled=raise_max_auto_disabled,
                ):
                    continue
                setattr(adv, field, val)

            shelf_enabled_field = "auto_shelf_bid_control_enabled"
            shelf_enabled = False
            shelf_enabled_header = edit_header(shelf_enabled_field)
            if shelf_enabled_header in row and not _is_blank(row[shelf_enabled_header]):
                try:
                    shelf_enabled = bool(
                        parse_edit_value(shelf_enabled_field, row[shelf_enabled_header])
                    )
                except ValueError as e:
                    raise AdvExcelImportError(
                        f"Строка {i}, колонка {shelf_enabled_header}: {e}"
                    ) from e

            if shelf_enabled or _row_has_non_blank_shelf_value(row):
                if len(adv.nmids or []) != 1:
                    raise AdvExcelImportError(
                        f"Строка {i}: bid control Excel поддерживает только РК с одним NMID"
                    )
                nmid = int(adv.nmids[0])
                shelf_settings = await _get_or_create_default_shelf_settings(
                    session, nmid=nmid
                )
                shelf_settings.currency = DEFAULT_CURRENCY
                for field in EDITABLE_SHELF_BID_CONTROL_COLUMNS:
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
                            f"Строка {i}, колонка {h}: {e}"
                        ) from e
                    if field == "auto_shelf_test_share":
                        shelf_settings.test_share = float(val)
                    elif field == "auto_shelf_target_test_impressions":
                        shelf_settings.target_test_impressions = int(val)
                    elif field == "auto_shelf_target_test_observation_minutes":
                        shelf_settings.target_test_observation_minutes = int(val)
                    elif field == "auto_shelf_max_bid_rub":
                        shelf_settings.max_bid_minor = int(val)
                    elif field == "auto_shelf_min_bid_distance_rub":
                        shelf_settings.min_bid_distance_minor = int(val)

            updated += 1
            if progress_callback is not None:
                awaitable = progress_callback(i, total)
                if awaitable is not None:
                    await awaitable

        await session.commit()

    return updated, max_cpo_decrease_effects
