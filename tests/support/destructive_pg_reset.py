"""Function-scoped PostgreSQL data reset для destructive integration tests.

Использует уже validated AsyncEngine (не создаёт новый на каждый reset
в production path — caller передаёт engine). Восстанавливает baseline
``wbcabinet`` id=1 после TRUNCATE.

Не выполняет DROP/CREATE schema — это session bootstrap.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

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


async def reset_postgres_test_data(
    engine: Any,
    *,
    restore_baseline: bool = True,
) -> None:
    """Очистить test PG data и восстановить immutable baseline rows.

    Args:
        engine: validated SQLAlchemy AsyncEngine к ``test_adv_bot_db``.
        restore_baseline: после TRUNCATE вставить wbcabinet id=1.

    Side effects:
        TRUNCATE ... CASCADE + optional seed. Не создаёт/не dispose engine.
    """
    async with engine.begin() as conn:
        await conn.execute(text(PG_TRUNCATE_SQL))
        if restore_baseline:
            await _restore_baseline_wbcabinet(conn)


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
