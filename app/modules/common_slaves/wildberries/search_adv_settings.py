"""Helpers that keep the legacy search AdvSetting row in sync with main auto rows.

ComplexAdv and parts of the UI still expect a dedicated ``AdvSetting`` row for the
search campaign where ``adv_id == main_adv.search_adv_id``. This helper preserves
that invariant without rewriting the broader dual-row model.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvSetting

_MISSING_SEARCH_ACTIVE_STATUS = "unknown"


async def ensure_search_adv_setting_for_main_adv(
    session: AsyncSession,
    main_adv: AdvSetting,
    search_adv_id: int,
    *,
    active_status: str | None = None,
    nmids: Sequence[int] | None = None,
) -> AdvSetting:
    """Ensure the legacy search-campaign row exists for the given main campaign.

    The helper creates a dedicated search row when it is missing and performs only
    targeted, non-destructive updates on existing rows. It intentionally avoids
    rewriting manual tuning fields such as CPM, bidder flags, limits, or names on
    already-existing rows.
    """
    resolved_nmids = list(nmids) if nmids is not None else list(main_adv.nmids or [])
    resolved_status = active_status

    result = await session.execute(
        select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
    )
    search_adv = result.scalar_one_or_none()

    if search_adv is None:
        search_adv = AdvSetting(
            adv_id=search_adv_id,
            name=main_adv.name or f"search_adv_{search_adv_id}",
            max_place=main_adv.max_place,
            max_cpm=main_adv.max_cpm,
            active_status=resolved_status or _MISSING_SEARCH_ACTIVE_STATUS,
            wb_cabinet_id=main_adv.wb_cabinet_id,
            bidder_active=False,
            parsing_active=False,
            bot_active=bool(main_adv.bot_active),
            reset_place=bool(main_adv.reset_place),
            type=9,
            nmids=resolved_nmids,
            hard_min_ctr=getattr(main_adv, "hard_min_ctr", 0.1),
        )
        session.add(search_adv)
        await session.flush()
        return search_adv

    search_adv.wb_cabinet_id = main_adv.wb_cabinet_id
    if not search_adv.nmids and resolved_nmids:
        search_adv.nmids = resolved_nmids
    if active_status not in (None, _MISSING_SEARCH_ACTIVE_STATUS):
        search_adv.active_status = active_status
    if search_adv.type is None:
        search_adv.type = 9

    await session.flush()
    return search_adv
