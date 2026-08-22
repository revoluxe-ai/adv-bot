"""Function-scoped PostgreSQL data reset для destructive integration tests.

Использует уже validated AsyncEngine (не создаёт новый на каждый reset
в production path — caller передаёт engine). Восстанавливает baseline
``wbcabinet`` id=1 после TRUNCATE.

Не выполняет DROP/CREATE schema — это session bootstrap.

TRUNCATE берёт AccessExclusiveLock на все перечисленные таблицы; при
параллельных workers / overlapping sessions это даёт ``DeadlockDetectedError``.
Поэтому reset: (1) сериализует truncate через ``pg_advisory_xact_lock``,
(2) ретраит bounded deadlock.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

logger = logging.getLogger(__name__)

# Таблицы, которые часто мутируются destructive tests.
# Порядок не критичен при CASCADE; RESTART IDENTITY сбрасывает sequences.
PG_TRUNCATE_TABLES: tuple[str, ...] = (
    '"user"',
    "wbcabinet",
    "wbusercabinet",
    "wbbalancepayment",
    "wbbonuspayment",
    "payment",
    "keywordsetting",
    "advsetting",
    "balancereminder",
    "billing_event",
)

PG_TRUNCATE_SQL: str = (
    "TRUNCATE "
    + ", ".join(PG_TRUNCATE_TABLES)
    + " RESTART IDENTITY CASCADE"
)

# Стабильный ключ advisory-lock для сериализации test PG reset (signed int64).
PG_RESET_ADVISORY_LOCK_KEY: int = 874_512_903

# Bounded retry budget для DeadlockDetectedError на TRUNCATE.
PG_RESET_DEADLOCK_MAX_ATTEMPTS: int = 5
PG_RESET_DEADLOCK_BASE_DELAY_SEC: float = 0.05
PG_RESET_DEADLOCK_MAX_DELAY_SEC: float = 0.5


def is_pg_deadlock_error(exc: BaseException) -> bool:
    """True если исключение (или цепочка) — PostgreSQL deadlock ``40P01``.

    Args:
        exc: исходное или обёрнутое SQLAlchemy/asyncpg исключение.

    Returns:
        True для DeadlockDetectedError / sqlstate 40P01 / текста deadlock.
    """
    cur: BaseException | None = exc
    seen: set[int] = set()
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        name = type(cur).__name__
        if name in {"DeadlockDetectedError", "DeadlockDetected"}:
            return True
        sqlstate = getattr(cur, "sqlstate", None)
        if sqlstate == "40P01":
            return True
        orig = getattr(cur, "orig", None)
        if orig is not None and orig is not cur:
            orig_state = getattr(orig, "sqlstate", None)
            if orig_state == "40P01":
                return True
            if type(orig).__name__ in {"DeadlockDetectedError", "DeadlockDetected"}:
                return True
        if "deadlock detected" in str(cur).lower():
            return True
        cur = cur.__cause__ if cur.__cause__ is not None else cur.__context__
    return False


def _deadlock_backoff_sec(attempt: int) -> float:
    """Экспоненциальный backoff для deadlock retry (attempt 1-based)."""
    delay = PG_RESET_DEADLOCK_BASE_DELAY_SEC * (2 ** (attempt - 1))
    return float(min(delay, PG_RESET_DEADLOCK_MAX_DELAY_SEC))


async def reset_postgres_test_data(
    engine: Any,
    *,
    restore_baseline: bool = True,
    max_attempts: int = PG_RESET_DEADLOCK_MAX_ATTEMPTS,
    sleep_fn: Any = None,
) -> None:
    """Очистить test PG data и восстановить immutable baseline rows.

    Args:
        engine: validated SQLAlchemy AsyncEngine к ``test_adv_bot_db``.
        restore_baseline: после TRUNCATE вставить wbcabinet id=1.
        max_attempts: верхняя граница попыток при DeadlockDetectedError.
        sleep_fn: injectable async sleep ``(seconds) -> None`` (unit tests).

    Side effects:
        Advisory-locked TRUNCATE ... CASCADE + optional seed.
        Не создаёт/не dispose engine.

    Raises:
        Последний DeadlockDetectedError после исчерпания бюджета;
        любые non-deadlock ошибки без retry.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    _sleep = sleep_fn if sleep_fn is not None else asyncio.sleep
    last_exc: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            async with engine.begin() as conn:
                # Сериализация overlapping TRUNCATE между pytest workers/sessions.
                await conn.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": PG_RESET_ADVISORY_LOCK_KEY},
                )
                await conn.execute(text(PG_TRUNCATE_SQL))
                if restore_baseline:
                    await _restore_baseline_wbcabinet(conn)
            return
        except BaseException as exc:  # noqa: BLE001 — classify deadlock then decide
            last_exc = exc
            if not is_pg_deadlock_error(exc) or attempt >= max_attempts:
                raise
            delay = _deadlock_backoff_sec(attempt)
            logger.warning(
                "PG test reset deadlock on attempt %s/%s; retry in %.3fs: %s",
                attempt,
                max_attempts,
                delay,
                exc,
            )
            await _sleep(delay)

    assert last_exc is not None
    raise last_exc


async def _restore_baseline_wbcabinet(conn: Any) -> None:
    """Восстановить детерминированный baseline ``wbcabinet`` id=1."""
    from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

    initial_wb_cabinet_data = {
        "id": 1,
        "shop_id": "test_shop_id",
        "active": True,
        "expiration_time": datetime.now() + timedelta(days=7),
        "balance": 0.0,
        "bonus": 0.0,
        "demo": True,
        "expiration_alarm_days_pass": None,
    }
    insert_stmt = insert(WBCabinet).values(initial_wb_cabinet_data)
    on_conflict_stmt = insert_stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={k: v for k, v in initial_wb_cabinet_data.items() if k != "id"},
    )
    await conn.execute(on_conflict_stmt)
    await conn.execute(
        text(
            "SELECT setval(pg_get_serial_sequence('wbcabinet', 'id'), "
            "(SELECT COALESCE(MAX(id), 1) FROM wbcabinet));"
        )
    )


async def init_postgres_schema_and_seed(engine: Any) -> None:
    """Session-once: DROP/CREATE public schema + metadata.create_all + baseline.

    Caller обязан dispose engine снаружи (``await engine.dispose()``).
    """
    from app.utils.db.base import BaseTable as Base

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS public;"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        # Import models so metadata is populated.
        from app.modules.billing.event_manager.models import BillingEvent  # noqa: F401
        from app.modules.common_slaves.wildberries.models.models import (  # noqa: F401
            AdvKeyword,
            AdvSetting,
            KeywordSetting,
            WBAutoBudgetTopUp,
            WBBalancePayment,
            WBBonusPayment,
            WBCard,
            WBCategory,
            WBToken,
            WBUserCabinet,
        )
        from app.modules.wb_adv_updater.modules.balance_exp_informer.models import (  # noqa: F401
            BalanceReminder,
        )
        from app.utils.db.models import Invite, User  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        await _restore_baseline_wbcabinet(conn)
