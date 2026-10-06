"""Read-only ZIP assembler: ExportService → family gaps → encode_package."""

from __future__ import annotations

from app.modules.ai_package_v1.domain.export_period import ExportPeriod
from app.modules.ai_package_v1.export.export_service import ExportService
from app.modules.ai_package_v1.export.family_gaps import attach_family_gaps
from app.modules.ai_package_v1.export.package_summary import attach_package_summary
from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.zip_transport.encode import encode_package


class PackageZipAssembler:
    """
    Единственная поверхность полного ZIP для одного магазина.

    Оркестрация только: все datasets собирает ``ExportService``; assembler
    добавляет ``PACKAGE_FAMILY_GAPS.json`` и вызывает ZIP transport.
    """

    def __init__(self, *, export_service: ExportService | None = None) -> None:
        self._export_service = export_service or ExportService()

    async def assemble_zip(
        self,
        shop_id: str,
        period: ExportPeriod,
        *,
        generated_at: str | None = None,
    ) -> bytes:
        """
        Собирает полный AI Package v1 ZIP для одного shop_id.

        Args:
            shop_id: Authoritative PG ``WBCabinet.shop_id`` (str).
            period: Bounded export period для legacy datasets.
            generated_at: ISO timestamp hook для тестов.

        Returns:
            ZIP bytes (manifest + payloads).
        """
        export_result = await self._export_service.export(
            shop_id,
            period,
            generated_at=generated_at,
        )
        enriched, _ = attach_family_gaps(export_result)
        with_summary, _ = attach_package_summary(enriched)
        return encode_package(with_summary.manifest, with_summary.payloads)

    async def assemble_zip_with_scope(
        self,
        shop_id: str,
        period: ExportPeriod,
        scope: list[ExportScopeAdv],
        *,
        generated_at: str | None = None,
    ) -> bytes:
        """
        ZIP export с предзагруженным scope (unit seam без PG).

        Args:
            shop_id: PG shop_id str.
            period: Период export.
            scope: Inventory из ``PgExportShopScopeReader``.
            generated_at: ISO hook.

        Returns:
            ZIP bytes.
        """
        export_result = await self._export_service.export_with_scope(
            shop_id,
            period,
            scope,
            generated_at=generated_at,
        )
        enriched, _ = attach_family_gaps(export_result)
        with_summary, _ = attach_package_summary(enriched)
        return encode_package(with_summary.manifest, with_summary.payloads)
