"""Compatibility shim for WB API models used by WB API code path.

This module re-exports models from the canonical location so that
older imports like `from app.core.legacy-wb_api_clients.models import WBToken, WBCabinetAccess`
continue to work without requiring deeper architectural changes.
"""

from app.modules.common_slaves.wildberries.models import WBToken
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

__all__ = ["WBToken", "WBCabinetAccess"]
