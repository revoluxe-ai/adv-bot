"""
Read/write configured ad control rows с доменной валидацией.

Unit-тесты используют in-memory fakes; integration — реальный PG (отдельно).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.registry import (
    FeatureValidationError,
    get_feature_definition,
)
from app.modules.ad_control_settings.domain.resolver_models import (
    CampaignFeatureSlot,
    ShopFeatureSlot,
)
from app.modules.ad_control_settings.persistence.models import (
    AdControlCampaignFeatureRow,
    AdControlShopFeatureRow,
)
from app.modules.ad_control_settings.persistence.payload_codec import (
    PayloadCodecError,
    encode_payload_json,
    payload_json_from_untyped,
)
from app.modules.ad_control_settings.persistence.state_token import (
    compute_ad_control_state_token,
)
from app.modules.ad_control_settings.domain.configured import ConfiguredFeaturePayload


class AdControlPersistenceError(ValueError):
    """Ошибка валидации или consistency при persistence."""


@dataclass(frozen=True, slots=True)
class ShopFeatureUpsert:
    """Intent записи shop feature (Apply / repository API)."""

    shop_id: str
    feature_id: AdControlFeatureId
    schema_version: int
    activation: ShopFeatureActivation
    payload: ConfiguredFeaturePayload | None


@dataclass(frozen=True, slots=True)
class CampaignFeatureUpsert:
    """Intent записи campaign feature."""

    campaign: CampaignRef
    feature_id: AdControlFeatureId
    schema_version: int
    mode: AdControlFeatureMode
    payload: ConfiguredFeaturePayload | None


class AdControlSettingsRepository:
    """Async PG repository для configured slots."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_shop_slots(
        self,
        shop_id: str,
    ) -> dict[AdControlFeatureId, ShopFeatureSlot]:
        """Загрузить все shop rows для магазина."""
        stmt = select(AdControlShopFeatureRow).where(
            AdControlShopFeatureRow.shop_id == shop_id
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        slots: dict[AdControlFeatureId, ShopFeatureSlot] = {}
        for row in rows:
            feature_id = AdControlFeatureId(row.feature_id)
            payload = payload_json_from_untyped(feature_id, row.payload_json)
            slots[feature_id] = ShopFeatureSlot(
                activation=ShopFeatureActivation(row.activation),
                payload=payload,
            )
        return slots

    async def load_campaign_slots(
        self,
        campaign: CampaignRef,
    ) -> dict[AdControlFeatureId, CampaignFeatureSlot]:
        """Загрузить campaign rows для ``(shop_id, advert_id)``."""
        stmt = select(AdControlCampaignFeatureRow).where(
            AdControlCampaignFeatureRow.shop_id == campaign.shop_id,
            AdControlCampaignFeatureRow.advert_id == campaign.advert_id,
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        slots: dict[AdControlFeatureId, CampaignFeatureSlot] = {}
        for row in rows:
            feature_id = AdControlFeatureId(row.feature_id)
            payload = payload_json_from_untyped(feature_id, row.payload_json)
            slots[feature_id] = CampaignFeatureSlot(
                mode=AdControlFeatureMode(row.mode),
                payload=payload,
            )
        return slots

    async def get_shop_row(
        self,
        shop_id: str,
        feature_id: AdControlFeatureId,
        schema_version: int,
    ) -> AdControlShopFeatureRow | None:
        stmt = select(AdControlShopFeatureRow).where(
            AdControlShopFeatureRow.shop_id == shop_id,
            AdControlShopFeatureRow.feature_id == feature_id.value,
            AdControlShopFeatureRow.schema_version == schema_version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_campaign_row(
        self,
        campaign: CampaignRef,
        feature_id: AdControlFeatureId,
        schema_version: int,
    ) -> AdControlCampaignFeatureRow | None:
        stmt = select(AdControlCampaignFeatureRow).where(
            AdControlCampaignFeatureRow.shop_id == campaign.shop_id,
            AdControlCampaignFeatureRow.advert_id == campaign.advert_id,
            AdControlCampaignFeatureRow.feature_id == feature_id.value,
            AdControlCampaignFeatureRow.schema_version == schema_version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_shop_feature(self, upsert: ShopFeatureUpsert) -> str:
        """
        Создать/обновить shop row; вернуть новый ``state_token``.

        Не коммитит сессию (вызывающий Apply Authority).
        """
        validate_shop_upsert(upsert)
        payload_json = None
        if upsert.payload is not None:
            payload_json = encode_payload_json(upsert.feature_id, upsert.payload)
        token = compute_ad_control_state_token(
            {
                "scope": "SHOP",
                "shop_id": upsert.shop_id,
                "feature_id": upsert.feature_id.value,
                "schema_version": upsert.schema_version,
                "activation": upsert.activation.value,
                "payload": payload_json,
            }
        )
        now = datetime.now(tz=UTC)
        existing = await self.get_shop_row(
            upsert.shop_id,
            upsert.feature_id,
            upsert.schema_version,
        )
        if existing is None:
            row = AdControlShopFeatureRow(
                shop_id=upsert.shop_id,
                feature_id=upsert.feature_id.value,
                schema_version=upsert.schema_version,
                activation=upsert.activation.value,
                payload_json=payload_json,
                state_token=token,
                updated_at=now,
            )
            self._session.add(row)
        else:
            existing.activation = upsert.activation.value
            existing.payload_json = payload_json
            existing.state_token = token
            existing.updated_at = now
        return token

    async def upsert_campaign_feature(self, upsert: CampaignFeatureUpsert) -> str:
        """Создать/обновить campaign row; вернуть новый ``state_token``."""
        validate_campaign_upsert(upsert)
        payload_json = None
        if upsert.payload is not None:
            payload_json = encode_payload_json(upsert.feature_id, upsert.payload)
        token = compute_ad_control_state_token(
            {
                "scope": "CAMPAIGN",
                "shop_id": upsert.campaign.shop_id,
                "advert_id": upsert.campaign.advert_id,
                "feature_id": upsert.feature_id.value,
                "schema_version": upsert.schema_version,
                "mode": upsert.mode.value,
                "payload": payload_json,
            }
        )
        now = datetime.now(tz=UTC)
        existing = await self.get_campaign_row(
            upsert.campaign,
            upsert.feature_id,
            upsert.schema_version,
        )
        if existing is None:
            row = AdControlCampaignFeatureRow(
                shop_id=upsert.campaign.shop_id,
                advert_id=upsert.campaign.advert_id,
                feature_id=upsert.feature_id.value,
                schema_version=upsert.schema_version,
                mode=upsert.mode.value,
                payload_json=payload_json,
                state_token=token,
                updated_at=now,
            )
            self._session.add(row)
        else:
            existing.mode = upsert.mode.value
            existing.payload_json = payload_json
            existing.state_token = token
            existing.updated_at = now
        return token


def validate_shop_upsert(upsert: ShopFeatureUpsert) -> None:
    definition = get_feature_definition(upsert.feature_id)
    if upsert.schema_version != definition.schema_version:
        raise AdControlPersistenceError("schema_version mismatch")
    if upsert.activation == ShopFeatureActivation.ENABLED and upsert.payload is None:
        raise AdControlPersistenceError("ENABLED shop feature requires payload")
    if upsert.activation == ShopFeatureActivation.DISABLED and upsert.payload is not None:
        raise AdControlPersistenceError("DISABLED shop feature must not carry payload")
    if upsert.payload is not None:
        try:
            encode_payload_json(upsert.feature_id, upsert.payload)
        except (FeatureValidationError, PayloadCodecError) as exc:
            raise AdControlPersistenceError(str(exc)) from exc


def validate_campaign_upsert(upsert: CampaignFeatureUpsert) -> None:
    definition = get_feature_definition(upsert.feature_id)
    if upsert.schema_version != definition.schema_version:
        raise AdControlPersistenceError("schema_version mismatch")
    if upsert.mode == AdControlFeatureMode.OVERRIDE and upsert.payload is None:
        raise AdControlPersistenceError("OVERRIDE requires payload")
    if upsert.mode != AdControlFeatureMode.OVERRIDE and upsert.payload is not None:
        raise AdControlPersistenceError("non-OVERRIDE must not persist payload")
    if upsert.payload is not None:
        try:
            encode_payload_json(upsert.feature_id, upsert.payload)
        except (FeatureValidationError, PayloadCodecError) as exc:
            raise AdControlPersistenceError(str(exc)) from exc


def shop_snapshot_from_rows(
    rows: Sequence[AdControlShopFeatureRow],
) -> Mapping[AdControlFeatureId, tuple[ShopFeatureActivation, ConfiguredFeaturePayload | None, str]]:
    """Построить snapshot map для dry-run (feature → activation, payload, token)."""
    out: dict[
        AdControlFeatureId,
        tuple[ShopFeatureActivation, ConfiguredFeaturePayload | None, str],
    ] = {}
    for row in rows:
        feature_id = AdControlFeatureId(row.feature_id)
        payload = payload_json_from_untyped(feature_id, row.payload_json)
        out[feature_id] = (
            ShopFeatureActivation(row.activation),
            payload,
            row.state_token,
        )
    return out
