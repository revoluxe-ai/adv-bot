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
from tests.unit.ai_package_v1.keyword_performance.conftest import FakeKeywordDeps
from tests.unit.ai_package_v1.test_export_settings_integration import _scope_for_shop
from tests.unit.ai_package_v1.test_package_zip_assembler import (
    GENERATED_AT,
    PERIOD,
    SHOP_ID,
    _export_service,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_package_summary_present_and_self_describing(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row], keyword_deps=fake_deps)
    assembler = PackageZipAssembler(export_service=service)
    zip_bytes = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=GENERATED_AT,
    )
    validate_zip_package(zip_bytes)
    _manifest, files = decode_package(zip_bytes)
    summary = json.loads(files[PACKAGE_SUMMARY_LOGICAL].decode("utf-8"))
    assert summary["document_kind"] == "package_summary"
    assert "campaign_identity" in summary
    assert summary["campaign_identity"]["campaign_id_equals_physical_adv_id"] is True
    assert summary["zip_determinism_contract"] == "PAYLOAD_HASH_ONLY"
    families = {f["family_id"]: f for f in summary["families"]}
    assert families["shop_product_orders_sales_feed"]["canonical_status"] == str(
        FamilyStatus.GAP,
    )
    assert families["campaign_settings_history"]["canonical_status"] == str(FamilyStatus.GAP)
    assert families["campaign_change_events"]["canonical_status"] == str(FamilyStatus.GAP)
    assert families["campaign_settings_current"]["canonical_status"] == str(
        FamilyStatus.PARTIAL,
    )
    assert "leg_role" in families["keyword_performance"]["join_keys"]
    data_map = json.loads(files["DATA_MAP.json"].decode("utf-8"))
    assert "leg_role" in data_map["datasets"]["keyword_daily"]["primary_key"]


@pytest.mark.asyncio
async def test_payload_deterministic_zip_differs_when_generated_at_changes(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    """Declared contract: payload file hashes stable; manifest timestamp changes ZIP."""
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row], keyword_deps=fake_deps)
    assembler = PackageZipAssembler(export_service=service)
    scope = _scope_for_shop()
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
    assert hashlib.sha256(zip_a).hexdigest() != hashlib.sha256(zip_b).hexdigest()
