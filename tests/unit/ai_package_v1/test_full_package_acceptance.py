"""
FULL_AI_PACKAGE_ACCEPTANCE_REPORT runner (unit fixtures, no production I/O).

Запуск: poetry run pytest -m unit tests/unit/ai_package_v1/test_full_package_acceptance.py -v
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from app.modules.ai_package_v1.domain.enums import FamilyStatus
from app.modules.ai_package_v1.export.package_summary import PACKAGE_SUMMARY_LOGICAL
from app.modules.ai_package_v1.export.package_zip_assembler import PackageZipAssembler
from app.modules.ai_package_v1.validator.package_validator import validate_zip_package
from app.modules.ai_package_v1.zip_transport.encode import decode_package, payload_sha256_map
from tests.unit.ai_package_v1.conftest import AssemblerFactory, make_adv_setting
from tests.unit.ai_package_v1.keyword_performance.conftest import FakeKeywordDeps
from tests.unit.ai_package_v1.test_package_zip_assembler import (
    GENERATED_AT,
    PERIOD,
    SHOP_ID,
    _export_service,
)
from tests.unit.ai_package_v1.test_export_settings_integration import _scope_for_shop

pytestmark = pytest.mark.unit


@dataclass
class AcceptanceReport:
    package_generated: bool
    manifest: str
    data_map: str
    package_summary: str
    family_status_explicit: bool
    determinism: str
    ai_readability: str

    def render(self) -> str:
        return "\n".join(
            [
                f"PACKAGE_GENERATED: {'YES' if self.package_generated else 'NO'}",
                f"MANIFEST: {self.manifest}",
                f"DATA_MAP: {self.data_map}",
                f"PACKAGE_SUMMARY: {self.package_summary}",
                f"FAMILY_STATUS_EXPLICIT: {'YES' if self.family_status_explicit else 'NO'}",
                f"DETERMINISM: {self.determinism}",
                f"AI_READABILITY: {self.ai_readability}",
            ],
        )


async def _run_once(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
    generated_at: str,
) -> tuple[bytes, AcceptanceReport]:
    row = make_adv_setting(adv_id=111, search_adv_id=222, shop_id=SHOP_ID)
    service = _export_service(assembler_factory, [row], keyword_deps=fake_deps)
    assembler = PackageZipAssembler(export_service=service)
    zip_bytes = await assembler.assemble_zip_with_scope(
        SHOP_ID,
        PERIOD,
        _scope_for_shop(),
        generated_at=generated_at,
    )
    validate_zip_package(zip_bytes)
    manifest, files = decode_package(zip_bytes)
    summary = json.loads(files[PACKAGE_SUMMARY_LOGICAL].decode("utf-8"))
    data_map = json.loads(files["DATA_MAP.json"].decode("utf-8"))
    explicit = all(
        FamilyStatus(f["family_status"])
        for f in summary["families"]
    ) and all(
        FamilyStatus(g["family_status"]) for g in json.loads(
            files["PACKAGE_FAMILY_GAPS.json"].decode("utf-8"),
        )["gaps"]
    )
    ai_ok = (
        summary.get("campaign_identity") is not None
        and summary.get("missing_zero_null") is not None
        and "leg_role" in data_map["datasets"]["keyword_daily"]["primary_key"]
    )
    report = AcceptanceReport(
        package_generated=True,
        manifest="PASS",
        data_map="PASS" if data_map.get("schema_version") else "FAIL",
        package_summary="PASS" if summary.get("document_kind") == "package_summary" else "FAIL",
        family_status_explicit=explicit,
        determinism="PASS",
        ai_readability="PASS" if ai_ok else "PARTIAL",
    )
    return zip_bytes, report


@pytest.mark.asyncio
async def test_full_ai_package_acceptance_twice(
    assembler_factory: AssemblerFactory,
    fake_deps: FakeKeywordDeps,
) -> None:
    """Two deterministic reruns: PAYLOAD_HASH_ONLY (per-file sha256), not ZIP bytes."""
    zip1, report1 = await _run_once(assembler_factory, fake_deps, GENERATED_AT)
    zip2, report2 = await _run_once(assembler_factory, fake_deps, GENERATED_AT)
    assert report1.render() == report2.render()
    hashes1 = payload_sha256_map(decode_package(zip1)[1])
    hashes2 = payload_sha256_map(decode_package(zip2)[1])
    assert hashes1 == hashes2
    assert report1.package_summary == "PASS"
    assert report1.family_status_explicit is True
    assert report1.ai_readability == "PASS"
