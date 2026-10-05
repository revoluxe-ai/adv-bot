"""PG read-only shop scope для AI Package v1 (inventory, не shop-runner orchestrator)."""

from app.modules.ai_package_v1.scope.dto import ExportScopeAdv
from app.modules.ai_package_v1.scope.pg_export_shop_scope_reader import (
    PgExportShopScopeReader,
)

__all__ = ["ExportScopeAdv", "PgExportShopScopeReader"]
