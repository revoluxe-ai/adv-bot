from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import AdvTimeSettings, AdvTimeWeekMask

FULL_DAY_MASK = (1 << 24) - 1


@dataclass
class TimeSettingsDbState:
    schedule_enabled: bool
    date_enabled: bool
    date_start: date | None
    date_end: date | None
    timezone: str
    masks_by_dow: dict[int, int]


def _now_expr():
    return sa.func.now()


class TimeSettingsRepository:
    async def load_for_adv(
        self,
        session: AsyncSession,
        adv_setting_id: int,
    ) -> TimeSettingsDbState | None:
        settings_stmt = sa.select(AdvTimeSettings).where(
            AdvTimeSettings.adv_setting_id == adv_setting_id
        )
        settings_result = await session.execute(settings_stmt)
        settings_row = settings_result.scalar_one_or_none()

        mask_stmt = sa.select(AdvTimeWeekMask.dow, AdvTimeWeekMask.hours_mask).where(
            AdvTimeWeekMask.adv_setting_id == adv_setting_id
        )
        mask_result = await session.execute(mask_stmt)
        masks_by_dow = {int(dow): int(mask) for dow, mask in mask_result.all()}

        if settings_row is None and not masks_by_dow:
            return None

        if settings_row is None:
            return TimeSettingsDbState(
                schedule_enabled=False,
                date_enabled=False,
                date_start=None,
                date_end=None,
                timezone="Europe/Moscow",
                masks_by_dow=masks_by_dow,
            )

        return TimeSettingsDbState(
            schedule_enabled=bool(settings_row.schedule_enabled),
            date_enabled=bool(settings_row.date_enabled),
            date_start=settings_row.date_start,
            date_end=settings_row.date_end,
            timezone=settings_row.timezone,
            masks_by_dow=masks_by_dow,
        )

    async def load_for_adv_ids(
        self,
        session: AsyncSession,
        adv_setting_ids: list[int],
    ) -> dict[int, TimeSettingsDbState | None]:
        """Load time settings for multiple adv_setting_ids in 2 queries (batch)."""
        if not adv_setting_ids:
            return {}

        settings_stmt = sa.select(AdvTimeSettings).where(
            AdvTimeSettings.adv_setting_id.in_(adv_setting_ids)
        )
        settings_result = await session.execute(settings_stmt)
        settings_by_id = {
            int(row.adv_setting_id): row for row in settings_result.scalars().all()
        }

        mask_stmt = sa.select(
            AdvTimeWeekMask.adv_setting_id,
            AdvTimeWeekMask.dow,
            AdvTimeWeekMask.hours_mask,
        ).where(AdvTimeWeekMask.adv_setting_id.in_(adv_setting_ids))
        mask_result = await session.execute(mask_stmt)
        masks_by_adv: dict[int, dict[int, int]] = {}
        for adv_id, dow, mask in mask_result.all():
            aid = int(adv_id)
            masks_by_adv.setdefault(aid, {})[int(dow)] = int(mask)

        result: dict[int, TimeSettingsDbState | None] = {}
        for aid in adv_setting_ids:
            settings_row = settings_by_id.get(aid)
            masks = masks_by_adv.get(aid, {})

            if settings_row is None and not masks:
                result[aid] = None
                continue
            if settings_row is None:
                result[aid] = TimeSettingsDbState(
                    schedule_enabled=False,
                    date_enabled=False,
                    date_start=None,
                    date_end=None,
                    timezone="Europe/Moscow",
                    masks_by_dow=masks,
                )
                continue
            result[aid] = TimeSettingsDbState(
                schedule_enabled=bool(settings_row.schedule_enabled),
                date_enabled=bool(settings_row.date_enabled),
                date_start=settings_row.date_start,
                date_end=settings_row.date_end,
                timezone=settings_row.timezone,
                masks_by_dow=masks,
            )
        return result

    async def patch_toggle_hour(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        dow: int,
        hour: int,
        enabled: bool,
    ) -> None:
        bit_mask = 1 << hour
        clear_mask = FULL_DAY_MASK ^ bit_mask
        insert_mask = FULL_DAY_MASK if enabled else (FULL_DAY_MASK & clear_mask)
        update_expr = (
            AdvTimeWeekMask.hours_mask.op("|")(bit_mask)
            if enabled
            else AdvTimeWeekMask.hours_mask.op("&")(clear_mask)
        )

        stmt = pg_insert(AdvTimeWeekMask).values(
            adv_setting_id=adv_setting_id,
            dow=dow,
            hours_mask=insert_mask,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeWeekMask.adv_setting_id, AdvTimeWeekMask.dow],
            set_={"hours_mask": update_expr},
        )
        await session.execute(stmt)

    async def patch_day_mask(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        dow: int,
        mask: int,
    ) -> None:
        stmt = pg_insert(AdvTimeWeekMask).values(
            adv_setting_id=adv_setting_id,
            dow=dow,
            hours_mask=mask,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeWeekMask.adv_setting_id, AdvTimeWeekMask.dow],
            set_={"hours_mask": mask},
        )
        await session.execute(stmt)

    async def patch_range(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        dow: int,
        range_mask: int,
        enabled: bool,
    ) -> None:
        clear_mask = FULL_DAY_MASK ^ range_mask
        insert_mask = FULL_DAY_MASK if enabled else (FULL_DAY_MASK & clear_mask)
        update_expr = (
            AdvTimeWeekMask.hours_mask.op("|")(range_mask)
            if enabled
            else AdvTimeWeekMask.hours_mask.op("&")(clear_mask)
        )
        stmt = pg_insert(AdvTimeWeekMask).values(
            adv_setting_id=adv_setting_id,
            dow=dow,
            hours_mask=insert_mask,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeWeekMask.adv_setting_id, AdvTimeWeekMask.dow],
            set_={"hours_mask": update_expr},
        )
        await session.execute(stmt)

    async def patch_week_masks(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        masks_by_dow: dict[int, int],
    ) -> None:
        rows = [
            {"adv_setting_id": adv_setting_id, "dow": dow, "hours_mask": mask}
            for dow, mask in masks_by_dow.items()
        ]
        if not rows:
            return
        stmt = pg_insert(AdvTimeWeekMask).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeWeekMask.adv_setting_id, AdvTimeWeekMask.dow],
            set_={"hours_mask": stmt.excluded.hours_mask},
        )
        await session.execute(stmt)

    async def patch_copy_day(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        target_dows: list[int],
        source_mask: int,
    ) -> None:
        if not target_dows:
            return
        rows = [
            {"adv_setting_id": adv_setting_id, "dow": dow, "hours_mask": source_mask}
            for dow in target_dows
        ]
        stmt = pg_insert(AdvTimeWeekMask).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeWeekMask.adv_setting_id, AdvTimeWeekMask.dow],
            set_={"hours_mask": stmt.excluded.hours_mask},
        )
        await session.execute(stmt)

    async def patch_schedule_enabled(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        enabled: bool,
    ) -> None:
        stmt = pg_insert(AdvTimeSettings).values(
            adv_setting_id=adv_setting_id,
            schedule_enabled=enabled,
            timezone="Europe/Moscow",
            updated_at=_now_expr(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeSettings.adv_setting_id],
            set_={
                "schedule_enabled": enabled,
                "updated_at": _now_expr(),
            },
        )
        await session.execute(stmt)

    async def patch_date_enabled(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        enabled: bool,
    ) -> None:
        stmt = pg_insert(AdvTimeSettings).values(
            adv_setting_id=adv_setting_id,
            date_enabled=enabled,
            timezone="Europe/Moscow",
            updated_at=_now_expr(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeSettings.adv_setting_id],
            set_={
                "date_enabled": enabled,
                "updated_at": _now_expr(),
            },
        )
        await session.execute(stmt)

    async def patch_dates(
        self,
        session: AsyncSession,
        adv_setting_id: int,
        date_start: date | None,
        date_end: date | None,
        date_enabled: bool,
    ) -> None:
        stmt = pg_insert(AdvTimeSettings).values(
            adv_setting_id=adv_setting_id,
            date_start=date_start,
            date_end=date_end,
            date_enabled=date_enabled,
            timezone="Europe/Moscow",
            updated_at=_now_expr(),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[AdvTimeSettings.adv_setting_id],
            set_={
                "date_start": date_start,
                "date_end": date_end,
                "date_enabled": date_enabled,
                "updated_at": _now_expr(),
            },
        )
        await session.execute(stmt)

