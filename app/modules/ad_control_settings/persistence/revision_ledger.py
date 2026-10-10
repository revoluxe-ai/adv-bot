"""Persistent monotonic mutation revision per logical ad control slot."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.ad_control_settings.persistence.models import AdControlSlotMutationLedger

SHOP_SCOPE = "SHOP"
CAMPAIGN_SCOPE = "CAMPAIGN"
_SHOP_ADVERT_SENTINEL = 0


@dataclass(frozen=True, slots=True)
class SlotMutationKey:
    """Logical slot identity for ledger allocation."""

    shop_id: str
    scope: str
    feature_id: AdControlFeatureId
    advert_id: int = _SHOP_ADVERT_SENTINEL

    @classmethod
    def for_shop(cls, shop_id: str, feature_id: AdControlFeatureId) -> SlotMutationKey:
        return cls(
            shop_id=shop_id,
            scope=SHOP_SCOPE,
            feature_id=feature_id,
            advert_id=_SHOP_ADVERT_SENTINEL,
        )

    @classmethod
    def for_campaign(
        cls,
        campaign: CampaignRef,
        feature_id: AdControlFeatureId,
    ) -> SlotMutationKey:
        return cls(
            shop_id=campaign.shop_id,
            scope=CAMPAIGN_SCOPE,
            feature_id=feature_id,
            advert_id=campaign.advert_id,
        )


async def allocate_mutation_revision(
    session: AsyncSession,
    key: SlotMutationKey,
) -> int:
    """
    Atomically increment slot mutation revision (survives row delete/recreate).

    Uses PostgreSQL ``INSERT ... ON CONFLICT DO UPDATE RETURNING``.
    """
    stmt = (
        insert(AdControlSlotMutationLedger)
        .values(
            shop_id=key.shop_id,
            scope=key.scope,
            advert_id=key.advert_id,
            feature_id=key.feature_id.value,
            last_mutation_revision=1,
        )
        .on_conflict_do_update(
            constraint="uq_ad_control_slot_mutation_ledger",
            set_={
                "last_mutation_revision": AdControlSlotMutationLedger.last_mutation_revision
                + 1,
            },
        )
        .returning(AdControlSlotMutationLedger.last_mutation_revision)
    )
    result = await session.execute(stmt)
    revision = result.scalar_one()
    return int(revision)


async def read_mutation_revision(
    session: AsyncSession,
    key: SlotMutationKey,
) -> int | None:
    """Current ledger revision if slot was ever mutated; else None."""
    stmt = select(AdControlSlotMutationLedger.last_mutation_revision).where(
        AdControlSlotMutationLedger.shop_id == key.shop_id,
        AdControlSlotMutationLedger.scope == key.scope,
        AdControlSlotMutationLedger.advert_id == key.advert_id,
        AdControlSlotMutationLedger.feature_id == key.feature_id.value,
    )
    result = await session.execute(stmt)
    value = result.scalar_one_or_none()
    return int(value) if value is not None else None
