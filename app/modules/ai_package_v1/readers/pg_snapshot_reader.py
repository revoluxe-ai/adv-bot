"""PG inventory snapshot: ids/relations из scope §1.2 (без detailed settings)."""

from __future__ import annotations

from collections.abc import Sequence

from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.scope.pg_export_shop_scope_reader import (
    PgExportShopScopeReader,
)


class PgSnapshotReader:
    """
    Read-only inventory seam (S10): scope DTO → stable inventory rows.

    Не добавляет колонок bids/budgets/strategy; не вызывает WB API.
    """

    def __init__(
        self,
        *,
        scope_reader: PgExportShopScopeReader | None = None,
    ) -> None:
        self._scope_reader = scope_reader or PgExportShopScopeReader()

    def inventory_rows(self, scope: Sequence[ExportScopeAdv]) -> list[ExportScopeAdv]:
        """
        Детерминированный список inventory строк из уже загруженного scope.

        Args:
            scope: DTO из ``PgExportShopScopeReader`` (allowlisted поля).

        Returns:
            Отсортированная копия scope (без повторного PG round-trip).
        """
        return sorted(scope, key=lambda row: row.auto_adv_id)

    async def load_inventory(self, shop_id: str) -> list[ExportScopeAdv]:
        """
        Загружает inventory через read-only PG scope reader.

        Args:
            shop_id: Authoritative ``WBCabinet.shop_id``.

        Returns:
            Inventory rows (может быть пустым).
        """
        scope = await self._scope_reader.load_scope(shop_id)
        return self.inventory_rows(scope)
