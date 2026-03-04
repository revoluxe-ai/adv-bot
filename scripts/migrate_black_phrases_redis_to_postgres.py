"""Migrate black_phrases (template of non-relevant key phrases) from Redis to Postgres.

Idempotent: only updates AdvSetting.black_phrases when it is currently empty ([]).
Does not delete keys from Redis. Run: poetry run python scripts/migrate_black_phrases_redis_to_postgres.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add project root for imports when run as script
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

import dotenv

_ = dotenv.load_dotenv()

from sqlalchemy import select, update

from app.core.redis_manager.redis_client import redis_client
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)

CHUNK_SIZE = 5000


def _redis_key_for_adv(name: str, adv_id: int | None, bot_active: bool, active_status: str) -> str:
    """Build Redis key matching AdvSetting.__repr__ (used by legacy RedisManager)."""
    return f"black_phrases:name: {name}, adverdId: {adv_id}, bot_active: {bot_active}, active_status: {active_status}"


def _parse_black_phrases_value(raw: bytes) -> list[str]:
    """Parse Redis value: JSON array or legacy CSV. Matches redis_manager.get_black_phrases logic."""
    if not raw or raw == b"":
        return []
    data = raw.decode("utf-8")
    # Legacy CSV format (not JSON)
    if not data.startswith("[") and not data.startswith("{"):
        return [p.strip() for p in data.split(",") if p.strip()]
    return json.loads(data)


def _is_empty_black_phrases(value: list[str] | None) -> bool:
    """True if black_phrases is empty or None (idempotent: safe to overwrite from Redis)."""
    return value is None or len(value) == 0


async def migrate_black_phrases_redis_to_postgres() -> None:
    """Copy black_phrases from Redis to AdvSetting.black_phrases. Idempotent."""
    migrated = 0
    skipped_already_filled = 0
    skipped_empty_redis = 0
    offset = 0

    columns = (
        AdvSetting.id,
        AdvSetting.name,
        AdvSetting.adv_id,
        AdvSetting.bot_active,
        AdvSetting.active_status,
        AdvSetting.black_phrases,
    )
    stmt_base = select(*columns).order_by(AdvSetting.id)

    try:
        while True:
            stmt = stmt_base.limit(CHUNK_SIZE).offset(offset)
            async with sm(read_only=True) as session:
                result = await session.execute(stmt)
                rows = result.all()
            if not rows:
                break

            for row in rows:
                if not _is_empty_black_phrases(row.black_phrases):
                    skipped_already_filled += 1
                    continue

                key = _redis_key_for_adv(
                    row.name, row.adv_id, row.bot_active, row.active_status
                )
                raw = await redis_client.get(key)
                if not raw or raw == b"":
                    skipped_empty_redis += 1
                    continue

                phrases = _parse_black_phrases_value(raw)
                if not phrases:
                    continue

                async with sm(read_only=False) as session:
                    _ = await session.execute(
                        update(AdvSetting)
                        .where(AdvSetting.id == row.id)
                        .values(black_phrases=phrases)
                    )
                    await session.commit()
                migrated += 1
                logger.info("Migrated adv_setting id=%s (%s phrases)", row.id, len(phrases))

            offset += len(rows)
            logger.debug("Processed chunk offset=%s size=%s", offset - len(rows), len(rows))
    finally:
        await redis_client.aclose()  # type: ignore[attr-defined]

    logger.info(
        "Done: migrated=%s, skipped_already_filled=%s, skipped_empty_redis=%s",
        migrated,
        skipped_already_filled,
        skipped_empty_redis,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(migrate_black_phrases_redis_to_postgres())


if __name__ == "__main__":
    main()
