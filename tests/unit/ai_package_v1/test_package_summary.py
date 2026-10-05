"""Contract tests for PACKAGE_SUMMARY.json and FamilyStatus semantics."""

from __future__ import annotations

import hashlib
import json
import pytest
from app.modules.ai_package_v1.domain.enums import FamilyStatus
from app.modules.ai_package_v1.export.package_summary import PACKAGE_SUMMARY_LOGICAL
from app.modules.ai_package_v1.export.package_zip_assembler import PackageZipAssembler
from app.modules.ai_package_v1.validator.package_validator import validate_zip_package
from app.modules.ai_package_v1.zip_transport.encode import decode_package, payload_sha256_map
from tests.unit.ai_package_v1.conftest import AssemblerFactory, make_adv_setting
from typing import Any, cast

from tests.unit.ai_package_v1.keyword_performance.conftest import FakeKeywordDeps
from tests.unit.ai_package_v1.package_zip_test_support import (
    GENERATED_AT,
    PERIOD,
    SHOP_ID,
    build_export_service_for_zip,
    scope_for_shop,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_package_summary_present_and_self_describing(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = build_export_service_for_zip(assembler_factory, [row], keyword_deps=fake_deps)
    assembler = PackageZipAssembler(export_service=service)
    zip_bytes = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    validate_zip_package(zip_bytes)
    manifest, files = decode_package(zip_bytes)
    summary = json.loads(files[PACKAGE_SUMMARY_LOGICAL].decode("utf-8"))
    raw_summary = files[PACKAGE_SUMMARY_LOGICAL].decode("utf-8")
    assert "CARD_MISSING" not in raw_summary
    assert summary["document_kind"] == "package_summary"
    assert "campaign_identity" in summary
    identity = summary["campaign_identity"]
    assert identity["campaign_id_equals_physical_adv_id"] is True
    assert identity["physical_wb_adv_id"]["column_name_in_campaign_full_stat_csv"] == "campaign_id"
    assert summary["zip_determinism_contract"] == "PAYLOAD_HASH_ONLY"
    families = {f["family_id"]: f for f in summary["families"]}
    assert families["shop_common_sales"]["family_status"] == str(FamilyStatus.GAP)
    assert families["campaign_settings_current"]["family_status"] == str(FamilyStatus.PARTIAL)
    assert families["campaign_settings_current"]["slice_kind"] == "CURRENT"
    assert families["campaign_advertising"]["family_status"] == str(FamilyStatus.PARTIAL)
    assert families["campaign_settings_history"]["family_status"] == str(FamilyStatus.GAP)
    assert families["campaign_change_events"]["family_status"] == str(FamilyStatus.GAP)
    assert "leg_role" in families["keyword_performance"]["primary_join_keys"]
    kw = families["keyword_performance"]
    assert kw["dataset_ids"]
    assert "keyword_daily" in kw["dataset_ids"]
    assert all(
        p.startswith("keyword_performance/") or p in ("DATA_MAP.json", "coverage.json")
        for p in kw["data_pointers"]
        if "keyword" in p or p.endswith(".jsonl")
    )
    assert families["campaign_advertising"].get("first_available_date") is None
    current_settings = cast(dict[str, Any], families["campaign_settings_current"])
    assert str(current_settings.get("family_notes", "")).startswith(
        "CampaignSettingsSnapshotV1"
    )
    current_semantics = cast(dict[str, str], current_settings["value_semantics"])
    assert "JSON" in current_semantics["missing"] or "CampaignSettingsSnapshotV1" in current_semantics["missing"]
    assert "CSV" not in current_semantics["missing"].lower()
    sales_card = next(
        c
        for c in manifest["datasets"]
        if c.get("dataset_id") == "shop_product_orders_sales"
    )
    assert sales_card.get("family_status") == "GAP"
    assert "row_count" not in sales_card
    assert "row_count" not in families["campaign_settings_history"]
    assert "row_count" not in families["shop_common_sales"]
    assert len(summary["gap_catalog_family_ids"]) == 7
    for card in manifest["datasets"]:
        if card.get("dataset_id") in ("package_summary", "package_family_gaps"):
            continue
        assert "family_status" in card
        assert card["family_status"] in {
            "COMPLETE",
            "PARTIAL",
            "GAP",
            "UNSUPPORTED",
            "FAILED",
        }
    for family_obj in summary["families"]:
        family = cast(dict[str, Any], family_obj)
        semantics_raw = family.get("value_semantics")
        assert isinstance(semantics_raw, dict)
        semantics = cast(dict[str, Any], semantics_raw)
        assert "missing" in semantics
        assert semantics["missing"] != semantics.get("zero", "")
    assert summary["missing_zero_null"]["invariant"] == "missing_row != numeric_zero != json_null"
    data_map = json.loads(files["DATA_MAP.json"].decode("utf-8"))
    assert data_map["campaign_identity"]["campaign_id_equals_physical_adv_id"] is True
    assert "leg_role" in data_map["datasets"]["keyword_daily"]["primary_key"]


@pytest.mark.asyncio
async def test_payload_deterministic_zip_differs_when_generated_at_changes(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    """Declared contract: payload file hashes stable; manifest timestamp changes ZIP."""
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = build_export_service_for_zip(assembler_factory, [row], keyword_deps=fake_deps)
    assembler = PackageZipAssembler(export_service=service)
    scope = scope_for_shop()
    zip_a = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        scope,
        generated_at="2026-10-05T12:00:00Z",
    )
    zip_b = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        scope,
        generated_at="2026-10-05T13:00:00Z",
    )
    _, files_a = decode_package(zip_a)
    _, files_b = decode_package(zip_b)
    hashes_a = payload_sha256_map(files_a)
    hashes_b = payload_sha256_map(files_b)
    stable_names = (
        "datasets/campaign_full_stat.csv",
        "datasets/complex_adv_funnel.csv",
    )
    for name in stable_names:
        assert hashes_a[name] == hashes_b[name]
    # ZIP bytes may differ; contract is payload hashes for stable domain files only.
    zip_hash_a = hashlib.sha256(zip_a).hexdigest()
    zip_hash_b = hashlib.sha256(zip_b).hexdigest()
    assert zip_hash_a != zip_hash_b or hashes_a != hashes_b
