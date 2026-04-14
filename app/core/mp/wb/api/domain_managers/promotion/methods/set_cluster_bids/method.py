from __future__ import annotations

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids import (
    NormqueryBidsAdapter,
    SetNormqueryBidsCommand,
    SetNormqueryBidsCommandItem,
)
import logging

from app.core.mp.wb.api.excs import BadRequestError

from .parse_min_bid_from_error import parse_min_bid_from_bad_request_detail

logger = logging.getLogger(__name__)


async def _post_normquery_batch_with_one_bid_too_low_retry(
    normquery_bids_adapter: NormqueryBidsAdapter,
    batch: list[SetNormqueryBidsCommandItem],
) -> None:
    """Один retry при ``wrong bid value`` + ``min: N`` (аналог legacy update_cpm)."""
    command = SetNormqueryBidsCommand(bids=batch)
    try:
        await normquery_bids_adapter.post_adv_v0_normquery_bids(command)
        return
    except BadRequestError as first_exc:
        min_bid = parse_min_bid_from_bad_request_detail(first_exc.detail)
        if min_bid is None:
            logger.error(
                "Ошибка обновления ставки кластера (без retry): %s, %s",
                command.bids,
                first_exc,
            )
            raise first_exc
        adjusted = [
            item.model_copy(update={"bid": max(item.bid, min_bid)}) for item in batch
        ]
        if all(a.bid == b.bid for a, b in zip(adjusted, batch, strict=True)):
            logger.error(
                "wrong bid value: min из ответа не изменил ставки batch=%s detail=%s",
                batch,
                first_exc.detail[:500] if first_exc.detail else "",
            )
            raise first_exc
        retry_cmd = SetNormqueryBidsCommand(bids=adjusted)
        try:
            await normquery_bids_adapter.post_adv_v0_normquery_bids(retry_cmd)
        except BadRequestError as second_exc:
            logger.error(
                "Ошибка обновления ставки кластера после retry min=%s: %s, %s",
                min_bid,
                retry_cmd.bids,
                second_exc,
            )
            raise second_exc


async def set_cluster_bids(
    normquery_bids_adapter: NormqueryBidsAdapter,
    bids: list[SetNormqueryBidsCommandItem],
) -> None:
    if not bids:
        return None
    batch_len = 100
    offset = 0
    while offset < len(bids):
        batch = bids[offset : offset + batch_len]
        await _post_normquery_batch_with_one_bid_too_low_retry(
            normquery_bids_adapter, batch
        )
        offset += batch_len
    return None