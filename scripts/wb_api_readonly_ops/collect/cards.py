"""Cards list pagination — полный card payload для всех карточек."""

from __future__ import annotations

from typing import Any, cast

from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
    PostContentV2GetCardsListBody,
    PostContentV2GetCardsListBodySettings,
    PostContentV2GetCardsListBodySettingsCursor,
    PostContentV2GetCardsListBodySettingsFilter,
    PostContentV2GetCardsListBodySettingsSort,
)
from app.core.mp.wb.api.generated.products.v1.content_products_client.types import UNSET

from scripts.wb_api_readonly_ops.collect.api_budget import ApiCallBudget
from scripts.wb_api_readonly_ops.collect.coverage import CompletenessStatus, CoverageEntry
from scripts.wb_api_readonly_ops.collect.jsonable import jsonable
from scripts.wb_api_readonly_ops.collect.raw_store import RawStore
from scripts.wb_api_readonly_ops.mutation_guard import assert_read_only_op


def _card_as_dict(card: object) -> dict[str, Any]:
    """Сериализовать карточку без обхода MagicMock __dict__."""
    if isinstance(card, dict):
        return cast(dict[str, Any], card)
    to_dict = getattr(card, "to_dict", None)
    if callable(to_dict):
        result = to_dict()
        if isinstance(result, dict):
            return cast(dict[str, Any], result)
    as_dict = jsonable(card)
    if isinstance(as_dict, dict):
        return cast(dict[str, Any], as_dict)
    return {"value": as_dict}


async def collect_cards(
    wb_data_manager: object,
    *,
    store: RawStore,
    budget: ApiCallBudget,
    page_limit: int = 100,
    max_pages: int = 10_000,
) -> tuple[list[int], list[dict[str, Any]]]:
    """Cursor pagination POST /content/v2/get/cards/list; full payload каждой карточки."""
    assert_read_only_op("get_cards_list")
    dm = cast(Any, wb_data_manager)
    pm = dm.products_manager

    filter_ = PostContentV2GetCardsListBodySettingsFilter(with_photo=-1)
    cursor = PostContentV2GetCardsListBodySettingsCursor(limit=page_limit)
    sort = PostContentV2GetCardsListBodySettingsSort(ascending=True)
    settings = PostContentV2GetCardsListBodySettings(
        filter_=filter_, cursor=cursor, sort=sort
    )
    body = PostContentV2GetCardsListBody(settings=settings)

    cards: list[dict[str, Any]] = []
    nmids: list[int] = []
    pages = 0
    api_calls = 0
    termination = "empty_page"

    while pages < max_pages:
        budget.consume()
        api_calls += 1
        response = await pm.get_cards_list(body=body)
        pages += 1
        if response is None:
            termination = "null_response"
            break
        cards_raw = response.cards
        page_cards: list[Any] = []
        if cards_raw is not UNSET and cards_raw:
            page_cards = list(cards_raw)
        for card in page_cards:
            as_dict = _card_as_dict(card)
            cards.append(as_dict)
            raw_nm = as_dict.get("nmID") or as_dict.get("nm_id")
            if raw_nm is not None:
                try:
                    nmids.append(int(raw_nm))
                except (TypeError, ValueError):
                    pass
        if len(page_cards) < page_limit:
            termination = "short_page"
            break
        resp_cursor = response.cursor
        if resp_cursor is UNSET:
            termination = "no_cursor"
            break
        updated_at = getattr(resp_cursor, "updated_at", UNSET)
        next_nm_id = getattr(resp_cursor, "nm_id", UNSET)
        if updated_at is UNSET and next_nm_id is UNSET:
            termination = "cursor_unset"
            break
        next_cursor = PostContentV2GetCardsListBodySettingsCursor(
            limit=page_limit,
            updated_at=updated_at if updated_at is not UNSET else None,
            nm_id=next_nm_id if next_nm_id is not UNSET else None,
        )
        body = PostContentV2GetCardsListBody(
            settings=PostContentV2GetCardsListBodySettings(
                filter_=filter_, cursor=next_cursor, sort=sort
            )
        )

    entry = CoverageEntry(
        family="cards_read",
        endpoint="/content/v2/get/cards/list",
        method="POST",
        http_statuses=[200],
        api_calls=api_calls,
        pagination_used=pages > 1,
        pagination_pages=pages,
        unique_nmids=len(set(nmids)),
        completeness=(
            CompletenessStatus.FULL_AVAILABLE
            if cards
            else CompletenessStatus.EMPTY
        ),
        notes=[f"cursor_termination={termination}", "historical_coverage=CURRENT_STATE_ONLY"],
    )
    store.write_jsonl("cards/cards.jsonl", cards, entry=entry)
    return nmids, cards
