"""Contract tests for PackageZipAssembler (one shop, one ZIP, family gaps)."""

from __future__ import annotations

import importlib
import json
import sys
import pytest

from app.modules.ai_package_v1.export.family_gaps import PACKAGE_FAMILY_GAPS_LOGICAL
from app.modules.ai_package_v1.export.package_zip_assembler import PackageZipAssembler
from app.modules.ai_package_v1.validator.package_validator import validate_zip_package
from app.modules.ai_package_v1.zip_transport.encode import decode_package, payload_sha256_map
from tests.unit.ai_package_v1.conftest import AssemblerFactory, make_adv_setting
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
async def test_package_zip_assembler_includes_family_gaps_and_validates(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    """Full ZIP: gaps file present, validator passes."""
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
    _manifest, files = decode_package(zip_bytes)
    gaps_raw = files[PACKAGE_FAMILY_GAPS_LOGICAL]
    gaps_doc = json.loads(gaps_raw.decode("utf-8"))
    assert gaps_doc["document_kind"] == "package_family_gaps"
    assert len(gaps_doc["gaps"]) >= 1
    assert all(entry["family_status"] == "GAP" for entry in gaps_doc["gaps"])


@pytest.mark.asyncio
async def test_package_zip_payload_hash_deterministic(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    """Идентичные входы → идентичные per-file content sha256 (PAYLOAD_HASH_ONLY)."""
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = build_export_service_for_zip(assembler_factory, [row], keyword_deps=fake_deps)
    assembler = PackageZipAssembler(export_service=service)
    scope = scope_for_shop()
    first = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        scope,
        generated_at=GENERATED_AT,
    )
    second = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        scope,
        generated_at=GENERATED_AT,
    )
    _, files_first = decode_package(first)
    _, files_second = decode_package(second)
    assert payload_sha256_map(files_first) == payload_sha256_map(files_second)


def test_cli_module_does_not_import_wb_promotion_clients() -> None:
    """CLI boundary: no WB HTTP stack on import."""
    saved = dict(sys.modules)
    try:
        for name in list(sys.modules):
            if name.startswith("app.core.mp.wb"):
                del sys.modules[name]
        importlib.import_module("scripts.ai_package_v1_export")
        wb_loaded = any(
            name.startswith("app.core.mp.wb.api")
            for name in sys.modules
            if name not in saved
        )
        assert not wb_loaded
    finally:
        for name in list(sys.modules):
            if name not in saved:
                del sys.modules[name]
        sys.modules.update(saved)
