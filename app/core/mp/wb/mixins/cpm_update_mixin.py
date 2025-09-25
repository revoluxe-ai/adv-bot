from __future__ import annotations

"""Миксин для обновления CPM ставок."""

import logging

from app.shared.application.dto.update_bids_in_advs.update_bids_search_adv_ids_batch import (
    UpdateBidsSearchAdvInShopBatch,
    UpdateBidForNmidCommand,
)
from app.core.di import inject

logger = logging.getLogger(__name__)


class CPMUpdateMixin:
    """Миксин для управления ставками CPM."""
   pass