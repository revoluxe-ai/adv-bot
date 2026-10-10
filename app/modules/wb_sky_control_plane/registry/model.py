"""ORM registry для stable opaque cmp_* resource identity."""

from __future__ import annotations

from sqlalchemy import Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class WbSkyCampaignResourceRegistry(BaseTable):
    """Registry existing logical campaign resources (отдельно от AdvSetting identity).

    Canonical identity не добавляется в AdvSetting; cmp_* id живёт только здесь.
    """

    resource_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    wb_cabinet_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    adv_setting_id: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    auto_adv_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_adv_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchor_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    backfill_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="active"
    )

    __table_args__ = (
        UniqueConstraint(
            "wb_cabinet_id",
            "anchor_fingerprint",
            name="uq_wbsky_registry_cabinet_anchor",
        ),
        Index("ix_wbsky_registry_auto_adv_id", "auto_adv_id"),
        Index("ix_wbsky_registry_search_adv_id", "search_adv_id"),
    )
