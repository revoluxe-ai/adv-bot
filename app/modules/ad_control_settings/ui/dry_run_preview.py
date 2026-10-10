"""
Сборка AdControlChangeSetV1 и dry-run без Apply и без записи.

Return-to-inherit = ``campaign.clear_ad_control_feature`` без payload магазина.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from app.modules.ad_control_settings.domain.configured import ConfiguredFeaturePayload
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId
from app.modules.ad_control_settings.domain.registry import (
    FeatureValidationError,
    get_feature_definition,
)
from app.modules.ad_control_settings.persistence.payload_codec import (
    PayloadCodecError,
    encode_payload_json,
)
from app.modules.wb_sky_control_plane.kernel.ad_control_validate import (
    AdControlCampaignFeatureSnapshotV1,
    AdControlShopFeatureSnapshotV1,
    validate_ad_control_changeset,
)
from app.modules.wb_sky_control_plane.models.ad_control_changeset import (
    AdControlChangeSetMetadataV1,
    AdControlChangeSetV1,
    AdControlLogicalScopeV1,
    AdControlRevisionPreconditionV1,
    AdvertCampaignRefV1,
    CampaignFeatureTargetV1,
    CampaignOverridePayloadV1,
    ClearCampaignAdControlFeatureOperation,
    DisableCampaignAdControlFeatureOperation,
    SetCampaignAdControlOverrideOperation,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus

PreviewOp = (
    SetCampaignAdControlOverrideOperation
    | DisableCampaignAdControlFeatureOperation
    | ClearCampaignAdControlFeatureOperation
)


@dataclass(frozen=True, slots=True)
class DryRunPreview:
    """Результат preview. ``persisted`` всегда False."""

    operation: str
    expected_revision: int | None
    validation_status: str
    diff_lines: tuple[str, ...]
    error_lines: tuple[str, ...]
    notes: tuple[str, ...]
    persisted: bool = False


def preview_clear_to_inherit(
    *,
    shop_id: str,
    advert_id: int,
    feature_id: AdControlFeatureId,
    expected_revision: int | None,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> DryRunPreview:
    """Снять authority-строку кампании. Payload магазина в операцию не копируется."""
    operation = ClearCampaignAdControlFeatureOperation(
        operation_id=_operation_id(),
        preconditions=AdControlRevisionPreconditionV1(
            expected_revision=expected_revision
        ),
        resource=AdvertCampaignRefV1(shop_id=shop_id, advert_id=advert_id),
        payload=CampaignFeatureTargetV1(
            feature_id=feature_id,
            schema_version=_schema_version(feature_id),
        ),
    )
    return _validate(
        shop_id=shop_id,
        operation=operation,
        expected_revision=expected_revision,
        shop_snapshots=shop_snapshots,
        campaign_snapshots=campaign_snapshots,
        notes=(
            "clear удаляет authority кампании. "
            "INHERIT не записывается отдельной строкой.",
        ),
    )


def preview_disable(
    *,
    shop_id: str,
    advert_id: int,
    feature_id: AdControlFeatureId,
    expected_revision: int | None,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> DryRunPreview:
    """Preview ``campaign.disable_ad_control_feature``."""
    operation = DisableCampaignAdControlFeatureOperation(
        operation_id=_operation_id(),
        preconditions=AdControlRevisionPreconditionV1(
            expected_revision=expected_revision
        ),
        resource=AdvertCampaignRefV1(shop_id=shop_id, advert_id=advert_id),
        payload=CampaignFeatureTargetV1(
            feature_id=feature_id,
            schema_version=_schema_version(feature_id),
        ),
    )
    return _validate(
        shop_id=shop_id,
        operation=operation,
        expected_revision=expected_revision,
        shop_snapshots=shop_snapshots,
        campaign_snapshots=campaign_snapshots,
        notes=("disable не копирует payload магазина.",),
    )


def preview_override_from_shop_payload(
    *,
    shop_id: str,
    advert_id: int,
    feature_id: AdControlFeatureId,
    expected_revision: int | None,
    shop_payload: ConfiguredFeaturePayload | None,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
) -> DryRunPreview:
    """
    Preview OVERRIDE с уже сконфигурированным shop payload.

    Это не возврат к наследованию: в desired попадает копия payload как OVERRIDE.
    Если shop payload нет — ChangeSet не строится.
    """
    if shop_payload is None:
        return DryRunPreview(
            operation="campaign.set_ad_control_override",
            expected_revision=expected_revision,
            validation_status=DryRunStatus.REJECTED.value,
            diff_lines=(),
            error_lines=("NO_CONFIGURED_SHOP_PAYLOAD",),
            notes=(
                "OVERRIDE не собран: у магазина нет payload. "
                "Пустое значение не подставлено.",
            ),
        )
    try:
        encoded = encode_payload_json(feature_id, shop_payload)
    except (FeatureValidationError, PayloadCodecError) as exc:
        return DryRunPreview(
            operation="campaign.set_ad_control_override",
            expected_revision=expected_revision,
            validation_status=DryRunStatus.REJECTED.value,
            diff_lines=(),
            error_lines=(str(exc),),
            notes=("payload не прошёл registry/codec. ChangeSet не отправлен.",),
        )
    operation = SetCampaignAdControlOverrideOperation(
        operation_id=_operation_id(),
        preconditions=AdControlRevisionPreconditionV1(
            expected_revision=expected_revision
        ),
        resource=AdvertCampaignRefV1(shop_id=shop_id, advert_id=advert_id),
        payload=CampaignOverridePayloadV1(
            feature_id=feature_id,
            schema_version=_schema_version(feature_id),
            payload=encoded,
        ),
    )
    return _validate(
        shop_id=shop_id,
        operation=operation,
        expected_revision=expected_revision,
        shop_snapshots=shop_snapshots,
        campaign_snapshots=campaign_snapshots,
        notes=(
            "Это OVERRIDE (копия текущего shop payload в preview). "
            "Не путать с возвратом к наследованию.",
        ),
    )


def _validate(
    *,
    shop_id: str,
    operation: PreviewOp,
    expected_revision: int | None,
    shop_snapshots: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    campaign_snapshots: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ],
    notes: tuple[str, ...],
) -> DryRunPreview:
    changeset = AdControlChangeSetV1(
        changeset_id=f"adc-ui-{uuid4().hex}",
        scope=AdControlLogicalScopeV1(shop_id=shop_id),
        operations=[operation],
        metadata=AdControlChangeSetMetadataV1(
            origin="telegram-ad-control-4.2a",
            reason="dry-run-preview",
        ),
    )
    result = validate_ad_control_changeset(
        changeset,
        shop_snapshots=shop_snapshots,
        campaign_snapshots=campaign_snapshots,
    )
    diff_lines = tuple(
        (
            f"{diff.intent.value} {diff.field_path}: "
            f"{diff.current} → {diff.desired}"
            + (
                f" after={diff.effective_source_after}"
                if diff.effective_source_after
                else ""
            )
        )
        for diff in result.diffs
    )
    error_lines = tuple(f"{error.code}: {error.message}" for error in result.errors)
    return DryRunPreview(
        operation=operation.op,
        expected_revision=expected_revision,
        validation_status=result.status.value,
        diff_lines=diff_lines,
        error_lines=error_lines,
        notes=notes,
    )


def _operation_id() -> str:
    return f"op-{uuid4().hex}"


def _schema_version(feature_id: AdControlFeatureId) -> int:
    return get_feature_definition(feature_id).schema_version
