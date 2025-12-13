from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids import (
    NormqueryBidsAdapter,
    SetNormqueryBidsCommand,
    SetNormqueryBidsCommandItem,
)
import logging

from app.core.mp.wb.api.excs import BadRequestError

logger = logging.getLogger(__name__)


async def set_cluster_bids(
    normquery_bids_adapter: NormqueryBidsAdapter,
    bids: list[SetNormqueryBidsCommandItem],
) -> None:
    if not bids:
        return None
    batch_len = 1
    offset = 0
    while offset < len(bids):
        batch = bids[offset:offset + batch_len]
        command = SetNormqueryBidsCommand(bids=batch)
        try:
            await normquery_bids_adapter.post_adv_v0_normquery_bids(command)
        except BadRequestError as e:
            logger.error("Ошибка обновления ставки кластера: %s, %s", command.bids, e)
        offset += batch_len
    return None