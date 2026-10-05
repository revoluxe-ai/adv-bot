"""Assembler detailed campaign settings snapshot из PG AdvSetting rows."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol, cast

from app.modules.ai_package_v1.domain.campaign_settings_snapshot_v1 import (
    CampaignLegSettingsV1,
    CampaignSettingsSnapshotRecordV1,
    CampaignSettingsSnapshotV1,
    CompletenessBlockV1,
    FieldProvenanceV1,
    InventoryRelationBlockV1,
    LocalPolicyBlockV1,
    SCHEMA_VERSION,
)
from app.modules.ai_package_v1.domain.settings_enums import (
    AuthorityClass,
    CampaignLegRole,
    SettingsCollectionOutcome,
    SettingsCoverageLevel,
    SettingsFreshnessLevel,
    SettingsReasonCode,
)
from app.modules.ai_package_v1.read.local_policy_projection import (
    project_local_policy_fields,
)
from app.modules.ai_package_v1.readers.pg_campaign_settings_reader import (
    PgCampaignSettingsReader,
)
from app.modules.common_slaves.wildberries.models.models import AdvSetting


class SettingsReaderProtocol(Protocol):
    """Контракт PG reader для assembler."""

    async def load_adv_settings(self, shop_id: str) -> list[AdvSetting]:
        ...


def _prov(
    field_path: str,
    authority_class: AuthorityClass,
    source_ref: str,
    *,
    observed_at: datetime | None = None,
    reason_codes: tuple[SettingsReasonCode, ...] = (),
) -> FieldProvenanceV1:
    return FieldProvenanceV1(
        field_path=field_path,
        authority_class=authority_class,
        source_ref=source_ref,
        observed_at=observed_at,
        reason_codes=reason_codes,
    )


def _build_inventory_block(row: AdvSetting, shop_id: str) -> InventoryRelationBlockV1:
    nmids = tuple(int(n) for n in (row.nmids or []))
    provenance = (
        _prov(
            "inventory.adv_setting_id",
            AuthorityClass.INVENTORY_RELATION,
            "pg:AdvSetting.id",
        ),
        _prov(
            "inventory.shop_id",
            AuthorityClass.INVENTORY_RELATION,
            "pg:WBCabinet.shop_id",
        ),
        _prov(
            "inventory.adv_id",
            AuthorityClass.INVENTORY_RELATION,
            "pg:AdvSetting.adv_id",
        ),
        _prov(
            "inventory.search_adv_id",
            AuthorityClass.INVENTORY_RELATION,
            "pg:AdvSetting.search_adv_id",
        ),
        _prov(
            "inventory.nmids",
            AuthorityClass.INVENTORY_RELATION,
            "pg:AdvSetting.nmids",
        ),
    )
    return InventoryRelationBlockV1(
        adv_setting_id=row.id,
        shop_id=shop_id,
        adv_id=row.adv_id,
        search_adv_id=row.search_adv_id,
        name=row.name,
        active_status=row.active_status,
        nmids=nmids,
        field_provenance=provenance,
    )


def _build_auto_leg(row: AdvSetting) -> CampaignLegSettingsV1 | None:
    adv_id = cast(int | None, row.adv_id)
    if adv_id is None:
        return None
    provenance: list[FieldProvenanceV1] = [
        _prov(
            "auto_leg.wb_adv_id",
            AuthorityClass.INVENTORY_RELATION,
            "pg:AdvSetting.adv_id",
        ),
        _prov(
            "auto_leg.wb_bid_type",
            AuthorityClass.WB_AUTHORITATIVE,
            "pg:AdvSetting.wb_bid_type",
            observed_at=row.last_update,
            reason_codes=(SettingsReasonCode.PARTIAL_PG_WB_SYNC,),
        ),
        _prov(
            "auto_leg.wb_placement_search",
            AuthorityClass.WB_AUTHORITATIVE,
            "pg:AdvSetting.wb_placement_search",
            observed_at=row.last_update,
            reason_codes=(SettingsReasonCode.PARTIAL_PG_WB_SYNC,),
        ),
        _prov(
            "auto_leg.wb_placement_recommendations",
            AuthorityClass.WB_AUTHORITATIVE,
            "pg:AdvSetting.wb_placement_recommendations",
            observed_at=row.last_update,
            reason_codes=(SettingsReasonCode.PARTIAL_PG_WB_SYNC,),
        ),
        _prov(
            "auto_leg.wb_status",
            AuthorityClass.UNSUPPORTED,
            "pg:unsynced",
            reason_codes=(
                SettingsReasonCode.UNSUPPORTED_FIELD,
                SettingsReasonCode.PARTIAL_PG_WB_SYNC,
            ),
        ),
        _prov(
            "auto_leg.wb_payment_type",
            AuthorityClass.UNSUPPORTED,
            "pg:unsynced",
            reason_codes=(
                SettingsReasonCode.UNSUPPORTED_FIELD,
                SettingsReasonCode.PARTIAL_PG_WB_SYNC,
            ),
        ),
    ]
    return CampaignLegSettingsV1(
        wb_adv_id=adv_id,
        leg_role=CampaignLegRole.AUTO,
        wb_bid_type=row.wb_bid_type,
        wb_placement_search=row.wb_placement_search,
        wb_placement_recommendations=row.wb_placement_recommendations,
        field_provenance=tuple(provenance),
    )


def _build_search_leg(row: AdvSetting) -> CampaignLegSettingsV1 | None:
    search_id = row.search_adv_id
    if search_id is None:
        return None
    provenance: list[FieldProvenanceV1] = [
        _prov(
            "search_leg.wb_adv_id",
            AuthorityClass.INVENTORY_RELATION,
            "pg:AdvSetting.search_adv_id",
        ),
        _prov(
            "search_leg.wb_bid_type",
            AuthorityClass.UNKNOWN,
            "pg:missing_search_leg_sync",
            reason_codes=(
                SettingsReasonCode.UNKNOWN,
                SettingsReasonCode.PARTIAL_PG_WB_SYNC,
            ),
        ),
        _prov(
            "search_leg.wb_status",
            AuthorityClass.UNSUPPORTED,
            "pg:unsynced",
            reason_codes=(
                SettingsReasonCode.UNSUPPORTED_FIELD,
                SettingsReasonCode.PARTIAL_PG_WB_SYNC,
            ),
        ),
    ]
    return CampaignLegSettingsV1(
        wb_adv_id=search_id,
        leg_role=CampaignLegRole.SEARCH,
        wb_bid_type=None,
        field_provenance=tuple(provenance),
    )


def _build_local_policy_block(row: AdvSetting) -> LocalPolicyBlockV1:
    fields = project_local_policy_fields(row)
    provenance = (
        _prov(
            "local_policy.bot_active",
            AuthorityClass.LOCAL_POLICY,
            "pg:AdvSetting.bot_active",
            observed_at=row.last_update,
        ),
        _prov(
            "local_policy.budget",
            AuthorityClass.LOCAL_POLICY,
            "pg:AdvSetting.budget_columns",
            observed_at=row.last_update,
        ),
        _prov(
            "local_policy.sales",
            AuthorityClass.LOCAL_POLICY,
            "pg:AdvSetting.sales_columns",
            observed_at=row.last_update,
        ),
        _prov(
            "local_policy.bid_control",
            AuthorityClass.LOCAL_POLICY,
            "pg:AdvSetting.bid_control_columns",
            observed_at=row.last_update,
        ),
        _prov(
            "local_policy.keyword_policy",
            AuthorityClass.LOCAL_POLICY,
            "pg:AdvSetting.keyword_jsonb",
            observed_at=row.last_update,
        ),
    )
    return LocalPolicyBlockV1(
        bot_active=fields["bot_active"],
        bidder_active=fields["bidder_active"],
        parsing_active=fields["parsing_active"],
        budget=fields["budget"],
        sales=fields["sales"],
        bid_control=fields["bid_control"],
        keyword_policy=fields["keyword_policy"],
        field_provenance=provenance,
    )


def _record_completeness() -> CompletenessBlockV1:
    return CompletenessBlockV1(
        collection_outcome=SettingsCollectionOutcome.SUCCESS,
        coverage=SettingsCoverageLevel.PARTIAL,
        reason_codes=(SettingsReasonCode.PARTIAL_PG_WB_SYNC,),
        freshness=SettingsFreshnessLevel.UNKNOWN,
    )


def _package_completeness(
    record_count: int,
) -> CompletenessBlockV1:
    if record_count == 0:
        return CompletenessBlockV1(
            collection_outcome=SettingsCollectionOutcome.NO_DATA,
            coverage=SettingsCoverageLevel.UNKNOWN,
            reason_codes=(
                SettingsReasonCode.NO_DATA,
                SettingsReasonCode.PARTIAL_PG_WB_SYNC,
            ),
            freshness=SettingsFreshnessLevel.UNKNOWN,
        )
    return CompletenessBlockV1(
        collection_outcome=SettingsCollectionOutcome.SUCCESS,
        coverage=SettingsCoverageLevel.PARTIAL,
        reason_codes=(SettingsReasonCode.PARTIAL_PG_WB_SYNC,),
        freshness=SettingsFreshnessLevel.UNKNOWN,
    )


class CampaignSettingsAssembler:
    """Собирает CampaignSettingsSnapshotV1 из read-only PG inventory."""

    def __init__(
        self,
        reader: SettingsReaderProtocol | None = None,
        *,
        session_maker: object | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if reader is not None:
            self._reader = reader
        elif session_maker is not None:
            self._reader = PgCampaignSettingsReader(session_maker)  # type: ignore[arg-type]
        else:
            raise ValueError("reader or session_maker required")
        self._clock = clock or (lambda: datetime.now(tz=UTC))

    async def assemble(self, shop_id: str) -> CampaignSettingsSnapshotV1:
        """Собрать point-in-time snapshot для shop_id.

        Args:
            shop_id: WBCabinet.shop_id.

        Returns:
            Domain payload с provenance; PG-only slice 1 (PARTIAL WB sync).
        """
        rows = await self._reader.load_adv_settings(shop_id)
        assembled_at = self._clock()
        records: list[CampaignSettingsSnapshotRecordV1] = []
        for row in rows:
            cabinet = cast(object | None, row.wb_cabinet)
            cabinet_shop_id = getattr(cabinet, "shop_id", None)
            if cabinet_shop_id != shop_id:
                continue
            records.append(
                CampaignSettingsSnapshotRecordV1(
                    inventory=_build_inventory_block(row, shop_id),
                    auto_leg=_build_auto_leg(row),
                    search_leg=_build_search_leg(row),
                    local_policy=_build_local_policy_block(row),
                    record_completeness=_record_completeness(),
                )
            )
        return CampaignSettingsSnapshotV1(
            schema_version=SCHEMA_VERSION,
            shop_id=shop_id,
            snapshot_assembled_at=assembled_at,
            records=tuple(records),
            completeness=_package_completeness(len(records)),
        )
