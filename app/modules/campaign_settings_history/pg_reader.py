"""PostgreSQL read adapter for campaign settings history.

Spec: campaign-settings-history.
All queries are SELECT-only and batch by cabinet; current settings remain PG authority.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.campaign_settings_contract import (
    HistoryPolicy,
    REGISTERED_SOURCES,
    CampaignSettingsSources,
)
from app.modules.common_slaves.wildberries.models import (
    AdvSetting,
    AdvTimeSettings,
    AdvTimeWeekMask,
    AutoShelfBidControlSettings,
    KeywordSetting,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet

from .domain import CabinetSettingsBatch, CampaignSettingsRecord


def _history_input_row(source_name: str, obj: object) -> dict[str, object]:
    """Project only explicitly history-included fields from one ORM row."""
    result: dict[str, object] = {}
    source = REGISTERED_SOURCES[source_name]
    for field_name, policy in source.fields.items():
        if policy.history is HistoryPolicy.EXCLUDED:
            continue
        if source_name == "AdvSetting" and field_name == "_search_adv_id":
            result[field_name] = getattr(obj, "search_adv_id")
        else:
            result[field_name] = getattr(obj, field_name)
    return result


class PostgresCampaignSettingsReader:
    """Batch SELECT adapter bound to caller-owned PostgreSQL transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def discover_cabinet_ids(self) -> tuple[int, ...]:
        """Discover cabinets owning settings rows, independent of active/runtime flags."""
        stmt = (
            select(AdvSetting.wb_cabinet_id)
            .distinct()
            .order_by(AdvSetting.wb_cabinet_id)
        )
        result = await self._session.execute(stmt)
        return tuple(int(value) for value in result.scalars().all())

    async def load_cabinet(self, wb_cabinet_id: int) -> CabinetSettingsBatch:
        """Load one complete cabinet settings aggregate with bounded batch queries."""
        shop_stmt = select(WBCabinet.shop_id).where(WBCabinet.id == wb_cabinet_id)
        shop_result = await self._session.execute(shop_stmt)
        shop_id = shop_result.scalar_one()

        adv_stmt = (
            select(AdvSetting)
            .where(AdvSetting.wb_cabinet_id == wb_cabinet_id)
            .order_by(AdvSetting.id)
        )
        adv_result = await self._session.execute(adv_stmt)
        adv_rows = list(adv_result.scalars().unique().all())
        if not adv_rows:
            return CabinetSettingsBatch(
                wb_cabinet_id=wb_cabinet_id,
                shop_id=str(shop_id),
                campaigns=(),
            )

        adv_ids = [int(row.id) for row in adv_rows]

        keyword_stmt = (
            select(KeywordSetting)
            .where(KeywordSetting.adv_setting_id.in_(adv_ids))
            .order_by(KeywordSetting.adv_setting_id, KeywordSetting.text)
        )
        keyword_result = await self._session.execute(keyword_stmt)
        keywords_by_adv: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in keyword_result.scalars().all():
            keywords_by_adv[int(row.adv_setting_id)].append(
                _history_input_row("KeywordSetting", row)
            )

        all_nmids = sorted(
            {
                int(nmid)
                for adv in adv_rows
                for nmid in (adv.nmids or [])
            }
        )
        shelf_by_nmid: dict[int, dict[str, object]] = {}
        if all_nmids:
            shelf_stmt = (
                select(AutoShelfBidControlSettings)
                .where(AutoShelfBidControlSettings.nmid.in_(all_nmids))
                .order_by(AutoShelfBidControlSettings.nmid)
            )
            shelf_result = await self._session.execute(shelf_stmt)
            shelf_by_nmid = {
                int(row.nmid): _history_input_row(
                    "AutoShelfBidControlSettings",
                    row,
                )
                for row in shelf_result.scalars().all()
            }

        time_stmt = (
            select(AdvTimeSettings)
            .where(AdvTimeSettings.adv_setting_id.in_(adv_ids))
            .order_by(AdvTimeSettings.adv_setting_id)
        )
        time_result = await self._session.execute(time_stmt)
        time_by_adv = {
            int(row.adv_setting_id): _history_input_row("AdvTimeSettings", row)
            for row in time_result.scalars().all()
        }

        mask_stmt = (
            select(AdvTimeWeekMask)
            .where(AdvTimeWeekMask.adv_setting_id.in_(adv_ids))
            .order_by(AdvTimeWeekMask.adv_setting_id, AdvTimeWeekMask.dow)
        )
        mask_result = await self._session.execute(mask_stmt)
        masks_by_adv: dict[int, list[dict[str, object]]] = defaultdict(list)
        for row in mask_result.scalars().all():
            masks_by_adv[int(row.adv_setting_id)].append(
                _history_input_row("AdvTimeWeekMask", row)
            )

        campaigns: list[CampaignSettingsRecord] = []
        for adv in adv_rows:
            adv_setting_id = int(adv.id)
            adv_nmids = [int(nmid) for nmid in (adv.nmids or [])]
            shelf_rows = [
                shelf_by_nmid[nmid]
                for nmid in sorted(set(adv_nmids))
                if nmid in shelf_by_nmid
            ]
            effective_search_adv_id = getattr(adv, "search_adv_id")
            campaigns.append(
                CampaignSettingsRecord(
                    adv_setting_id=adv_setting_id,
                    wb_cabinet_id=wb_cabinet_id,
                    shop_id=str(shop_id),
                    adv_id=int(adv.adv_id),
                    search_adv_id=(
                        int(effective_search_adv_id)
                        if effective_search_adv_id is not None
                        else None
                    ),
                    sources=CampaignSettingsSources(
                        adv_setting=_history_input_row("AdvSetting", adv),
                        keyword_settings=tuple(
                            keywords_by_adv.get(adv_setting_id, ())
                        ),
                        auto_shelf_settings=tuple(shelf_rows),
                        adv_time_settings=time_by_adv.get(adv_setting_id),
                        adv_time_week_masks=tuple(
                            masks_by_adv.get(adv_setting_id, ())
                        ),
                    ),
                )
            )

        return CabinetSettingsBatch(
            wb_cabinet_id=wb_cabinet_id,
            shop_id=str(shop_id),
            campaigns=tuple(campaigns),
        )
