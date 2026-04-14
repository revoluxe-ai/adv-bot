from __future__ import annotations

import json
import logging
import re
from typing import Any, cast

from app.core.mp.wb.api.adapter.promotion_client.base_section_adapter import (
    BaseSectionAdapter,
)
from app.core.mp.wb.api.adapter.raise_errors import with_raise_errors
from app.core.mp.wb.api.excs import BadRequestError
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.api.sozdanie_kampanij.post_api_advert_v1_bids_min import (
    asyncio_detailed,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.models import (
    PostApiAdvertV1BidsMinResponse200,
)
from app.core.mp.wb.api.generated.promotion.v2.marketing_and_promotions_client.types import (
    Response,
)
from app.core.mp.wb.api.retry_decorator import retry_decorator

from .command import GetMinBidsCommand, GetMinBidsCommandItem
from .command_to_body import convert as command_to_body
from .dto import MinBidForNmid
from .raw_response_to_dto import convert as response_to_dto

logger = logging.getLogger(__name__)

_NMS_NOT_BELONG_RE = re.compile(
    r"some\s+nms?\s+are\s+not\s+belong\s+to\s+advert",
    re.IGNORECASE,
)


def _bad_request_payload(exc: BadRequestError) -> dict[str, Any] | None:
    raw = exc.detail
    if not raw:
        return None
    try:
        parsed: Any = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return cast(dict[str, Any], parsed)


def _is_nms_not_belong_to_advert_error(exc: BadRequestError) -> bool:
    """True if WB rejected payload because some nm_ids do not belong to advert."""
    payload = _bad_request_payload(exc)
    if payload is not None:
        title = str(payload.get("title", "") or "")
        detail = str(payload.get("detail", "") or "")
        combined = f"{title}\n{detail}"
        if _NMS_NOT_BELONG_RE.search(combined):
            return True
    # Fallback: substring match on raw string (non-JSON or partial body)
    raw = exc.detail
    if not raw:
        return False
    try:
        if _NMS_NOT_BELONG_RE.search(raw):
            return True
    except TypeError:
        return False
    return False


def _request_id_from_bad_request(exc: BadRequestError) -> str | None:
    payload = _bad_request_payload(exc)
    if payload is None:
        return None
    rid = payload.get("request_id")
    return str(rid) if rid is not None else None


class MinBidsAdapter(BaseSectionAdapter):
    """Адаптер запросов минимальных ставок по товарам в рекламных кампаниях."""

    async def post_api_advert_v1_bids_min(
        self, command: GetMinBidsCommand
    ) -> list[list[MinBidForNmid]]:
        """POST ``/api/advert/v1/bids/min``: одно тело = один ``advert_id`` (см. сгенерированный
        ``PostApiAdvertV1BidsMinBody``). Разные РК — разные HTTP-запросы. Внутри одной РК в теле
        передаётся список ``nm_ids`` и список ``placement_types``; при ошибке «чужие nm» —
        bisection в ``_bisect_min_bids_for_item``.

        Возвращает по одному списку ``MinBidForNmid`` на каждый ``command_item`` (порядок как
        в ``command.items``), чтобы доменный слой не смешивал ответы разных РК в одном dict по
        ``nmid``."""
        grouped: list[list[MinBidForNmid]] = []
        for command_item in command.items:
            grouped.append(
                await self._post_api_advert_v1_bids_min_single(
                    command_item=command_item,
                )
            )
        return grouped

    async def _post_api_advert_v1_bids_min_single(
        self,
        command_item: GetMinBidsCommandItem,
    ) -> list[MinBidForNmid]:
        """Min bids для одного command_item; при invalid nm — bisection по nm_ids."""
        nmids = command_item.nmids
        if not nmids:
            return []
        return await self._bisect_min_bids_for_item(command_item)

    async def _bisect_min_bids_for_item(
        self, command_item: GetMinBidsCommandItem
    ) -> list[MinBidForNmid]:
        nmids = command_item.nmids
        try:
            return await self._http_post_min_bids(command_item)
        except BadRequestError as exc:
            if not _is_nms_not_belong_to_advert_error(exc):
                raise
            req_id = _request_id_from_bad_request(exc)
            if len(nmids) > 1:
                mid = len(nmids) // 2
                left_nm = nmids[:mid]
                right_nm = nmids[mid:]
                logger.warning(
                    "min_bids batch split: adv_id=%s placement=%s nmids=%s -> %s | %s "
                    "request_id=%s",
                    command_item.adv_id,
                    command_item.placement_type.value,
                    len(nmids),
                    len(left_nm),
                    len(right_nm),
                    req_id,
                )
                left_item = command_item.model_copy(update={"nmids": left_nm})
                right_item = command_item.model_copy(update={"nmids": right_nm})
                left_res = await self._bisect_min_bids_for_item(left_item)
                right_res = await self._bisect_min_bids_for_item(right_item)
                return left_res + right_res

            bad_nmid = nmids[0]
            logger.error(
                "min_bids invalid nmid for advert (dropped): adv_id=%s placement=%s "
                "nmid=%s request_id=%s detail=%s",
                command_item.adv_id,
                command_item.placement_type.value,
                bad_nmid,
                req_id,
                exc.detail[:500] if exc.detail else "",
            )
            return []

    # Лимит WB для /bids/min: ~5 запросов / ~10–15 с; period/limit = базовый интервал между вызовами.
    # 14/4 → 3.5 с давало 429; 60/5 → 12 с лучше, но пост-фикс логи всё ещё показывали 429 при next_pause 13–15 от API.
    # 80/5 → 16 с — не ниже типичного Retry-After из ответов.
    @retry_decorator(period=80, limit=5, max_delay=120)
    async def _http_post_min_bids(
        self,
        command_item: GetMinBidsCommandItem,
    ) -> list[MinBidForNmid]:
        client = await self.auth_client_handler.get_proxy_client(self)
        body = command_to_body(command_item)
        response: Response[PostApiAdvertV1BidsMinResponse200] = await with_raise_errors(
            asyncio_detailed,
            client,
            body=body,
        )
        parsed = response.parsed
        if parsed is None:
            return []
        return response_to_dto(parsed)
