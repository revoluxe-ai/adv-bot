from __future__ import annotations

"""Миксин для обновления CPM ставок."""

import logging

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidCommand,
)
from app.core.di import inject
from app.core.mp.wb.base_adapters.base_adapter import WBBaseAdapters

logger = logging.getLogger(__name__)


class CPMUpdateMixin(WBBaseAdapters):
    """Миксин для управления ставками CPM."""
    pass