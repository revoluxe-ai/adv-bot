"""Bulk UPDATE ``KeywordSetting.target_place`` (O(1) round-trip).

Используется epoch confirmed-intent и legacy setup PASS-путями, чтобы не
делать N отдельных ``session.execute`` на каждый keyword.
"""

from __future__ import annotations

from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import KeywordSetting


async def bulk_update_keyword_target_places(
    session: AsyncSession,
    updates: list[tuple[int, int]],
) -> None:
    """Одним UPDATE записать ``target_place`` для набора keyword_setting id.

    Args:
        session: injectable async PG session (WRITE).
        updates: пары ``(keyword_setting_id, target_place)``. Пустой список — no-op.

    Side effects:
        Один ``session.execute`` (не commit).
    """
    if not updates:
        return
    id_to_place: dict[int, int] = {
        int(ks_id): int(place) for ks_id, place in updates
    }
    stmt = (
        update(KeywordSetting)
        .where(KeywordSetting.id.in_(tuple(id_to_place.keys())))
        .values(
            target_place=case(
                id_to_place,
                value=KeywordSetting.id,
            )
        )
    )
    _ = await session.execute(stmt)
