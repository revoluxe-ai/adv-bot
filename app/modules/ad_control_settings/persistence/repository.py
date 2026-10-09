"""
Read/write configured ad control rows с доменной валидацией и CAS revision.

``expected_revision=None`` => authoritative row must be absent (create / idempotent clear).
``expected_revision=int`` => row must exist with that revision (update / disable / clear).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import ConfiguredFeaturePayload
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
from app.modules.ad_control_settings.persistence.cas import (
    AdControlMutationKind,
    AdControlMutationResult,
    PersistedInheritForbiddenError,
    RevisionConflictError,
    UnsupportedSchemaVersionError,
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
class CampaignOverrideUpsert:
    """Campaign OVERRIDE authority row."""

    campaign: CampaignRef
    feature_id: AdControlFeatureId
    schema_version: int
    payload: ConfiguredFeaturePayload


@dataclass(frozen=True, slots=True)
class CampaignDisableUpsert:
    """Campaign DISABLED authority row (explicit, not inherit)."""

    campaign: CampaignRef
    feature_id: AdControlFeatureId
    schema_version: int


@dataclass(frozen=True, slots=True)
class CampaignClearUpsert:
    """Remove campaign authority (return to INHERIT)."""

    campaign: CampaignRef
    feature_id: AdControlFeatureId


class AdControlSettingsRepository:
    """Async PG repository для configured slots."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load_shop_slots(
        self,
        shop_id: str,
    ) -> dict[AdControlFeatureId, ShopFeatureSlot]:
        """Загрузить все shop rows для магазина (one row per feature_id)."""
        stmt = select(AdControlShopFeatureRow).where(
            AdControlShopFeatureRow.shop_id == shop_id
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        slots: dict[AdControlFeatureId, ShopFeatureSlot] = {}
        for row in rows:
            feature_id = AdControlFeatureId(row.feature_id)
            if feature_id in slots:
                raise AdControlPersistenceError(
                    f"duplicate shop feature authority: {feature_id}"
                )
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
        """
        Загрузить campaign authority rows.

        Missing feature => resolver treats as INHERIT (not loaded here).
        """
        stmt = select(AdControlCampaignFeatureRow).where(
            AdControlCampaignFeatureRow.shop_id == campaign.shop_id,
            AdControlCampaignFeatureRow.advert_id == campaign.advert_id,
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        slots: dict[AdControlFeatureId, CampaignFeatureSlot] = {}
        for row in rows:
            feature_id = AdControlFeatureId(row.feature_id)
            if feature_id in slots:
                raise AdControlPersistenceError(
                    f"duplicate campaign feature authority: {feature_id}"
                )
            mode = AdControlFeatureMode(row.mode)
            if mode == AdControlFeatureMode.INHERIT:
                raise PersistedInheritForbiddenError(
                    f"persisted INHERIT forbidden for {feature_id}"
                )
            payload = payload_json_from_untyped(feature_id, row.payload_json)
            slots[feature_id] = CampaignFeatureSlot(mode=mode, payload=payload)
        return slots

    async def get_shop_row(
        self,
        shop_id: str,
        feature_id: AdControlFeatureId,
    ) -> AdControlShopFeatureRow | None:
        stmt = select(AdControlShopFeatureRow).where(
            AdControlShopFeatureRow.shop_id == shop_id,
            AdControlShopFeatureRow.feature_id == feature_id.value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_campaign_row(
        self,
        campaign: CampaignRef,
        feature_id: AdControlFeatureId,
    ) -> AdControlCampaignFeatureRow | None:
        stmt = select(AdControlCampaignFeatureRow).where(
            AdControlCampaignFeatureRow.shop_id == campaign.shop_id,
            AdControlCampaignFeatureRow.advert_id == campaign.advert_id,
            AdControlCampaignFeatureRow.feature_id == feature_id.value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def apply_shop_mutation(
        self,
        upsert: ShopFeatureUpsert,
        *,
        expected_revision: int | None,
    ) -> AdControlMutationResult:
        """CAS shop mutation; increments revision on success."""
        validate_shop_upsert(upsert)
        existing = await self.get_shop_row(upsert.shop_id, upsert.feature_id)
        if existing is None:
            if expected_revision is not None:
                raise RevisionConflictError("shop row absent but revision expected")
            return await self._insert_shop_row(upsert)

        if expected_revision is None:
            raise RevisionConflictError("shop row exists but create revision expected")
        if existing.revision != expected_revision:
            raise RevisionConflictError("stale shop revision")

        kind = _shop_mutation_kind(existing, upsert)
        if kind == AdControlMutationKind.NO_OP:
            return AdControlMutationResult(
                kind=kind,
                revision=existing.revision,
                state_token=existing.state_token,
            )

        payload_json = _shop_payload_json(upsert)
        new_revision = existing.revision + 1
        token = _shop_token(upsert, payload_json, new_revision)
        now = datetime.now(tz=UTC)
        stmt = (
            update(AdControlShopFeatureRow)
            .where(
                AdControlShopFeatureRow.id == existing.id,
                AdControlShopFeatureRow.revision == expected_revision,
            )
            .values(
                schema_version=upsert.schema_version,
                activation=upsert.activation.value,
                payload_json=payload_json,
                revision=new_revision,
                state_token=token,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            raise RevisionConflictError("concurrent shop update lost CAS race")

        return AdControlMutationResult(
            kind=kind,
            revision=new_revision,
            state_token=token,
        )

    async def apply_campaign_override(
        self,
        upsert: CampaignOverrideUpsert,
        *,
        expected_revision: int | None,
    ) -> AdControlMutationResult:
        validate_campaign_override_upsert(upsert)
        existing = await self.get_campaign_row(upsert.campaign, upsert.feature_id)
        if existing is None:
            if expected_revision is not None:
                raise RevisionConflictError("campaign row absent but revision expected")
            return await self._insert_campaign_override(upsert)

        if expected_revision is None:
            raise RevisionConflictError("campaign row exists but create revision expected")
        if existing.revision != expected_revision:
            raise RevisionConflictError("stale campaign revision")

        payload_json = encode_payload_json(upsert.feature_id, upsert.payload)
        new_revision = existing.revision + 1
        token = _campaign_token(
            upsert.campaign,
            upsert.feature_id,
            upsert.schema_version,
            AdControlFeatureMode.OVERRIDE,
            payload_json,
            new_revision,
        )
        now = datetime.now(tz=UTC)
        stmt = (
            update(AdControlCampaignFeatureRow)
            .where(
                AdControlCampaignFeatureRow.id == existing.id,
                AdControlCampaignFeatureRow.revision == expected_revision,
            )
            .values(
                schema_version=upsert.schema_version,
                mode=AdControlFeatureMode.OVERRIDE.value,
                payload_json=payload_json,
                revision=new_revision,
                state_token=token,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            raise RevisionConflictError("concurrent campaign override lost CAS race")

        return AdControlMutationResult(
            kind=AdControlMutationKind.UPDATE,
            revision=new_revision,
            state_token=token,
        )

    async def apply_campaign_disable(
        self,
        upsert: CampaignDisableUpsert,
        *,
        expected_revision: int | None,
    ) -> AdControlMutationResult:
        _assert_schema_supported(upsert.feature_id, upsert.schema_version)
        existing = await self.get_campaign_row(upsert.campaign, upsert.feature_id)
        if existing is None:
            if expected_revision is not None:
                raise RevisionConflictError("campaign row absent but revision expected")
            return await self._insert_campaign_disabled(upsert)

        if expected_revision is None:
            raise RevisionConflictError("campaign row exists but create revision expected")
        if existing.revision != expected_revision:
            raise RevisionConflictError("stale campaign revision")

        new_revision = existing.revision + 1
        token = _campaign_token(
            upsert.campaign,
            upsert.feature_id,
            upsert.schema_version,
            AdControlFeatureMode.DISABLED,
            None,
            new_revision,
        )
        now = datetime.now(tz=UTC)
        stmt = (
            update(AdControlCampaignFeatureRow)
            .where(
                AdControlCampaignFeatureRow.id == existing.id,
                AdControlCampaignFeatureRow.revision == expected_revision,
            )
            .values(
                schema_version=upsert.schema_version,
                mode=AdControlFeatureMode.DISABLED.value,
                payload_json=None,
                revision=new_revision,
                state_token=token,
                updated_at=now,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            raise RevisionConflictError("concurrent campaign disable lost CAS race")

        if (
            existing.mode == AdControlFeatureMode.DISABLED.value
            and existing.schema_version == upsert.schema_version
        ):
            return AdControlMutationResult(
                kind=AdControlMutationKind.NO_OP,
                revision=existing.revision,
                state_token=existing.state_token,
            )
        return AdControlMutationResult(
            kind=AdControlMutationKind.DISABLE,
            revision=new_revision,
            state_token=token,
        )

    async def clear_campaign_feature(
        self,
        upsert: CampaignClearUpsert,
        *,
        expected_revision: int | None,
    ) -> AdControlMutationResult:
        """Delete campaign authority; idempotent when already absent."""
        existing = await self.get_campaign_row(upsert.campaign, upsert.feature_id)
        if existing is None:
            if expected_revision is not None:
                raise RevisionConflictError("campaign row absent but revision expected")
            return AdControlMutationResult(
                kind=AdControlMutationKind.NO_OP,
                revision=None,
                state_token=None,
            )

        if expected_revision is None:
            raise RevisionConflictError("campaign row exists but absent revision expected")
        if existing.revision != expected_revision:
            raise RevisionConflictError("stale campaign revision for clear")

        stmt = (
            delete(AdControlCampaignFeatureRow)
            .where(
                AdControlCampaignFeatureRow.id == existing.id,
                AdControlCampaignFeatureRow.revision == expected_revision,
            )
        )
        result = await self._session.execute(stmt)
        if result.rowcount != 1:
            raise RevisionConflictError("concurrent campaign clear lost CAS race")

        return AdControlMutationResult(
            kind=AdControlMutationKind.CLEAR_TO_INHERIT,
            revision=None,
            state_token=None,
        )

    async def _insert_shop_row(self, upsert: ShopFeatureUpsert) -> AdControlMutationResult:
        payload_json = _shop_payload_json(upsert)
        revision = 1
        token = _shop_token(upsert, payload_json, revision)
        now = datetime.now(tz=UTC)
        row = AdControlShopFeatureRow(
            shop_id=upsert.shop_id,
            feature_id=upsert.feature_id.value,
            schema_version=upsert.schema_version,
            activation=upsert.activation.value,
            payload_json=payload_json,
            revision=revision,
            state_token=token,
            updated_at=now,
        )
        self._session.add(row)
        kind = (
            AdControlMutationKind.DISABLE
            if upsert.activation == ShopFeatureActivation.DISABLED
            else AdControlMutationKind.CREATE
        )
        return AdControlMutationResult(kind=kind, revision=revision, state_token=token)

    async def _insert_campaign_override(
        self,
        upsert: CampaignOverrideUpsert,
    ) -> AdControlMutationResult:
        payload_json = encode_payload_json(upsert.feature_id, upsert.payload)
        revision = 1
        token = _campaign_token(
            upsert.campaign,
            upsert.feature_id,
            upsert.schema_version,
            AdControlFeatureMode.OVERRIDE,
            payload_json,
            revision,
        )
        now = datetime.now(tz=UTC)
        self._session.add(
            AdControlCampaignFeatureRow(
                shop_id=upsert.campaign.shop_id,
                advert_id=upsert.campaign.advert_id,
                feature_id=upsert.feature_id.value,
                schema_version=upsert.schema_version,
                mode=AdControlFeatureMode.OVERRIDE.value,
                payload_json=payload_json,
                revision=revision,
                state_token=token,
                updated_at=now,
            )
        )
        return AdControlMutationResult(
            kind=AdControlMutationKind.CREATE,
            revision=revision,
            state_token=token,
        )

    async def _insert_campaign_disabled(
        self,
        upsert: CampaignDisableUpsert,
    ) -> AdControlMutationResult:
        revision = 1
        token = _campaign_token(
            upsert.campaign,
            upsert.feature_id,
            upsert.schema_version,
            AdControlFeatureMode.DISABLED,
            None,
            revision,
        )
        now = datetime.now(tz=UTC)
        self._session.add(
            AdControlCampaignFeatureRow(
                shop_id=upsert.campaign.shop_id,
                advert_id=upsert.campaign.advert_id,
                feature_id=upsert.feature_id.value,
                schema_version=upsert.schema_version,
                mode=AdControlFeatureMode.DISABLED.value,
                payload_json=None,
                revision=revision,
                state_token=token,
                updated_at=now,
            )
        )
        return AdControlMutationResult(
            kind=AdControlMutationKind.DISABLE,
            revision=revision,
            state_token=token,
        )


def _shop_payload_json(upsert: ShopFeatureUpsert) -> dict[str, object] | None:
    if upsert.payload is None:
        return None
    return encode_payload_json(upsert.feature_id, upsert.payload)


def _shop_token(
    upsert: ShopFeatureUpsert,
    payload_json: dict[str, object] | None,
    revision: int,
) -> str:
    return compute_ad_control_state_token(
        {
            "scope": "SHOP",
            "shop_id": upsert.shop_id,
            "feature_id": upsert.feature_id.value,
            "schema_version": upsert.schema_version,
            "activation": upsert.activation.value,
            "payload": payload_json,
            "revision": revision,
        }
    )


def _campaign_token(
    campaign: CampaignRef,
    feature_id: AdControlFeatureId,
    schema_version: int,
    mode: AdControlFeatureMode,
    payload_json: dict[str, object] | None,
    revision: int,
) -> str:
    return compute_ad_control_state_token(
        {
            "scope": "CAMPAIGN",
            "shop_id": campaign.shop_id,
            "advert_id": campaign.advert_id,
            "feature_id": feature_id.value,
            "schema_version": schema_version,
            "mode": mode.value,
            "payload": payload_json,
            "revision": revision,
        }
    )


def _shop_mutation_kind(
    existing: AdControlShopFeatureRow,
    upsert: ShopFeatureUpsert,
) -> AdControlMutationKind:
    payload_json = _shop_payload_json(upsert)
    if (
        existing.activation == upsert.activation.value
        and existing.schema_version == upsert.schema_version
        and existing.payload_json == payload_json
    ):
        return AdControlMutationKind.NO_OP
    if upsert.activation == ShopFeatureActivation.DISABLED:
        return AdControlMutationKind.DISABLE
    return AdControlMutationKind.UPDATE


def _assert_schema_supported(
    feature_id: AdControlFeatureId,
    schema_version: int,
) -> None:
    definition = get_feature_definition(feature_id)
    if schema_version != definition.schema_version:
        raise UnsupportedSchemaVersionError(
            f"unsupported schema_version {schema_version} for {feature_id}"
        )
    if schema_version > definition.schema_version:
        raise UnsupportedSchemaVersionError("newer unsupported schema")


def validate_shop_upsert(upsert: ShopFeatureUpsert) -> None:
    _assert_schema_supported(upsert.feature_id, upsert.schema_version)
    if upsert.activation == ShopFeatureActivation.ENABLED and upsert.payload is None:
        raise AdControlPersistenceError("ENABLED shop feature requires payload")
    if upsert.activation == ShopFeatureActivation.DISABLED and upsert.payload is not None:
        raise AdControlPersistenceError("DISABLED shop feature must not carry payload")
    if upsert.payload is not None:
        try:
            encode_payload_json(upsert.feature_id, upsert.payload)
        except (FeatureValidationError, PayloadCodecError) as exc:
            raise AdControlPersistenceError(str(exc)) from exc


def validate_campaign_override_upsert(upsert: CampaignOverrideUpsert) -> None:
    _assert_schema_supported(upsert.feature_id, upsert.schema_version)
    try:
        encode_payload_json(upsert.feature_id, upsert.payload)
    except (FeatureValidationError, PayloadCodecError) as exc:
        raise AdControlPersistenceError(str(exc)) from exc


def row_to_shop_snapshot(row: AdControlShopFeatureRow) -> tuple[
    ShopFeatureActivation,
    ConfiguredFeaturePayload | None,
    int,
    str,
]:
    """activation, payload, revision, state_token."""
    feature_id = AdControlFeatureId(row.feature_id)
    payload = payload_json_from_untyped(feature_id, row.payload_json)
    return (
        ShopFeatureActivation(row.activation),
        payload,
        row.revision,
        row.state_token,
    )


def row_to_campaign_snapshot(row: AdControlCampaignFeatureRow) -> tuple[
    AdControlFeatureMode,
    ConfiguredFeaturePayload | None,
    int,
    str,
    int,
]:
    """mode, payload, revision, state_token, schema_version."""
    feature_id = AdControlFeatureId(row.feature_id)
    mode = AdControlFeatureMode(row.mode)
    if mode == AdControlFeatureMode.INHERIT:
        raise PersistedInheritForbiddenError("persisted INHERIT in campaign row")
    payload = payload_json_from_untyped(feature_id, row.payload_json)
    return (
        mode,
        payload,
        row.revision,
        row.state_token,
        row.schema_version,
    )
