"""Снимки configured-строк для dry-run. Методы apply репозитория не вызываются."""

from __future__ import annotations

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.domain.registry import FEATURE_REGISTRY
from app.modules.ad_control_settings.persistence.repository import (
    AdControlSettingsRepository,
)
from app.modules.wb_sky_control_plane.kernel.ad_control_validate import (
    AdControlCampaignFeatureSnapshotV1,
    AdControlShopFeatureSnapshotV1,
)


async def load_dry_run_snapshots(
    repository: AdControlSettingsRepository,
    campaign: CampaignRef,
) -> tuple[
    dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1],
    dict[tuple[str, int, AdControlFeatureId], AdControlCampaignFeatureSnapshotV1],
]:
    """Прочитать ревизии shop/campaign slots. Отсутствующая строка не попадает в dict."""
    shop: dict[AdControlFeatureId, AdControlShopFeatureSnapshotV1] = {}
    for feature_id in FEATURE_REGISTRY:
        row = await repository.get_shop_row(campaign.shop_id, feature_id)
        if row is None:
            continue
        shop[feature_id] = AdControlShopFeatureSnapshotV1(
            feature_id=feature_id,
            schema_version=row.schema_version,
            activation=ShopFeatureActivation(row.activation),
            payload_json=_payload(row.payload_json),
            revision=row.revision,
            state_token=row.state_token,
        )
    campaign_snaps: dict[
        tuple[str, int, AdControlFeatureId],
        AdControlCampaignFeatureSnapshotV1,
    ] = {}
    for feature_id in FEATURE_REGISTRY:
        row = await repository.get_campaign_row(campaign, feature_id)
        if row is None:
            continue
        mode = AdControlFeatureMode(row.mode)
        campaign_snaps[(campaign.shop_id, campaign.advert_id, feature_id)] = (
            AdControlCampaignFeatureSnapshotV1(
                shop_id=campaign.shop_id,
                advert_id=campaign.advert_id,
                feature_id=feature_id,
                schema_version=row.schema_version,
                mode=mode,
                payload_json=_payload(row.payload_json),
                revision=row.revision,
                state_token=row.state_token,
            )
        )
    return shop, campaign_snaps


def _payload(raw: dict[str, object] | None) -> dict[str, object] | None:
    if raw is None:
        return None
    return dict(raw)
