"""Пагинация ассортимента магазина через ProductsManager.get_cards_list."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, cast

from app.core.mp.wb.api.excs import ApiForbiddenError
from app.core.mp.wb.api.domain_managers.products.products_manager import ProductsManager
from app.core.mp.wb.api.generated.products.v1.content_products_client.models import (
    PostContentV2GetCardsListBody,
    PostContentV2GetCardsListResponse200CardsItem,
)
from app.core.mp.wb.api.generated.products.v1.content_products_client.types import (
    UNSET,
    Unset,
)

logger = logging.getLogger(__name__)

DEFAULT_PAGE_LIMIT = 100
DEFAULT_MAX_PAGES = 200


@dataclass(frozen=True, slots=True)
class AssortmentPaginationResult:
    """Результат обхода Content API с доказательством пагинации."""

    nmids: frozenset[int]
    pages_completed: int
    terminal_empty_page: bool
    complete: bool
    partial_reason: str | None = None


class ShopAssortmentReader:
    """Читатель non-trash ассортимента магазина (universe A)."""

    def __init__(self, products_manager: ProductsManager) -> None:
        self._products_manager = products_manager

    async def paginate_all_nmids(
        self,
        *,
        page_limit: int = DEFAULT_PAGE_LIMIT,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> AssortmentPaginationResult:
        """
        Собрать все nmID non-trash карточек с fail-explicit при null/partial.

        Контракт пагинации (S01/S01c):
        - cursor.total — per-page count; полная страница требует progress + terminal;
        - UNSET/null/malformed cards/cursor не дают complete;
        - seen cursor + max_pages ограничивают бесконечные запросы;
        - повтор cursor / full page без progress → PARTIAL;
        - genuine 0-card terminal только при source-valid cursor.total=0 или empty
          после prior pages;
        - auth (ApiForbiddenError) и cancellation пробрасываются наверх;
        - прочие Content API ошибки → partial с proven nmIDs.
        """
        body = _build_cards_list_body(page_limit=page_limit)

        collected: set[int] = set()
        pages_completed = 0
        terminal_empty_page = False
        seen_cursors: set[tuple[str, int]] = set()
        prior_page_nmids: frozenset[int] = frozenset()

        while pages_completed < max_pages:
            try:
                response = await self._products_manager.get_cards_list(body=body)
            except asyncio.CancelledError:
                raise
            except ApiForbiddenError:
                raise
            except Exception as exc:
                logger.warning(
                    "Content API error during assortment pagination pages=%d: %s",
                    pages_completed,
                    exc,
                )
                return AssortmentPaginationResult(
                    nmids=frozenset(collected),
                    pages_completed=pages_completed,
                    terminal_empty_page=terminal_empty_page,
                    complete=False,
                    partial_reason=f"content_api_error:{type(exc).__name__}",
                )

            if response is None:
                return AssortmentPaginationResult(
                    nmids=frozenset(collected),
                    pages_completed=pages_completed,
                    terminal_empty_page=terminal_empty_page,
                    complete=False,
                    partial_reason="null_response",
                )

            cards_list, cards_error = _parse_cards(response.cards)
            if cards_error is not None:
                return AssortmentPaginationResult(
                    nmids=frozenset(collected),
                    pages_completed=pages_completed,
                    terminal_empty_page=terminal_empty_page,
                    complete=False,
                    partial_reason=cards_error,
                )

            pages_completed += 1
            page_nmids = _extract_valid_nmids(cards_list)

            if not cards_list:
                if pages_completed > 1 or _is_source_valid_empty_terminal(response):
                    terminal_empty_page = True
                    break
                return AssortmentPaginationResult(
                    nmids=frozenset(collected),
                    pages_completed=pages_completed,
                    terminal_empty_page=False,
                    complete=False,
                    partial_reason="empty_unconfirmed",
                )

            if page_nmids == prior_page_nmids and len(cards_list) >= page_limit:
                return AssortmentPaginationResult(
                    nmids=frozenset(collected),
                    pages_completed=pages_completed,
                    terminal_empty_page=False,
                    complete=False,
                    partial_reason="no_progress",
                )

            collected.update(page_nmids)
            prior_page_nmids = frozenset(page_nmids)

            if len(cards_list) < page_limit:
                break

            if _cursor_total_signals_terminal(response, page_limit):
                break

            next_body = _advance_body(
                body=body,
                cards_list=cards_list,
                response_cursor=response.cursor,
                page_limit=page_limit,
            )
            if next_body is None:
                return AssortmentPaginationResult(
                    nmids=frozenset(collected),
                    pages_completed=pages_completed,
                    terminal_empty_page=False,
                    complete=False,
                    partial_reason="malformed_cursor",
                )

            next_fp = _request_cursor_fingerprint(next_body)
            if next_fp is not None:
                if next_fp in seen_cursors:
                    return AssortmentPaginationResult(
                        nmids=frozenset(collected),
                        pages_completed=pages_completed,
                        terminal_empty_page=False,
                        complete=False,
                        partial_reason="cursor_loop",
                    )
                seen_cursors.add(next_fp)

            body = next_body

        if pages_completed >= max_pages:
            return AssortmentPaginationResult(
                nmids=frozenset(collected),
                pages_completed=pages_completed,
                terminal_empty_page=terminal_empty_page,
                complete=False,
                partial_reason="max_pages",
            )

        return AssortmentPaginationResult(
            nmids=frozenset(collected),
            pages_completed=pages_completed,
            terminal_empty_page=terminal_empty_page,
            complete=True,
            partial_reason=None,
        )


def _build_cards_list_body(
    *,
    page_limit: int,
    updated_at: str | None = None,
    nm_id: int | None = None,
    filter_dict: dict[str, Any] | None = None,
    sort_dict: dict[str, Any] | None = None,
) -> PostContentV2GetCardsListBody:
    """Собрать Content API body через typed ``from_dict`` (pyright-safe для attrs-моделей)."""
    cursor_payload: dict[str, Any] = {"limit": page_limit}
    if updated_at is not None:
        cursor_payload["updatedAt"] = updated_at
    if nm_id is not None:
        cursor_payload["nmID"] = nm_id
    settings_payload: dict[str, Any] = {
        "filter": filter_dict if filter_dict is not None else {"withPhoto": -1},
        "cursor": cursor_payload,
        "sort": sort_dict if sort_dict is not None else {"ascending": True},
    }
    return PostContentV2GetCardsListBody.from_dict({"settings": settings_payload})


def _parse_positive_int(value: object) -> int | None:
    """Положительный int; bool и не-int отклоняются."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    return None


def _valid_updated_at(value: object) -> bool:
    """updated_at cursor/card — непустая строка."""
    if value is UNSET or value is None:
        return False
    return isinstance(value, str) and bool(value.strip())


def _parse_cards(
    cards_raw: object,
) -> tuple[list[PostContentV2GetCardsListResponse200CardsItem], str | None]:
    """
    Распарсить cards из ответа Content API.

    UNSET/null/не-list → malformed (не трактуем как terminal empty).
    """
    if cards_raw is UNSET:
        return [], "malformed_cards_unset"
    if cards_raw is None:
        return [], "malformed_cards_null"
    if not isinstance(cards_raw, list):
        return [], "malformed_cards_type"
    return cast(list[PostContentV2GetCardsListResponse200CardsItem], cards_raw), None


def _extract_valid_nmids(
    cards_list: list[PostContentV2GetCardsListResponse200CardsItem],
) -> frozenset[int]:
    """Извлечь валидные positive-int nmID; bool/invalid пропускаются."""
    nmids: set[int] = set()
    for card in cards_list:
        raw_nm_id = card.nm_id
        if raw_nm_id is UNSET:
            continue
        nmid = _parse_positive_int(raw_nm_id)
        if nmid is not None:
            nmids.add(nmid)
    return frozenset(nmids)


def _parse_cursor_total(response: object) -> int | None:
    """Безопасно прочитать cursor.total (per-page count); malformed → None."""
    resp_cursor = getattr(response, "cursor", UNSET)
    if resp_cursor is UNSET:
        return None
    total = getattr(resp_cursor, "total", UNSET)
    if total is UNSET or total is None:
        return None
    if isinstance(total, bool):
        return None
    if isinstance(total, int) and total >= 0:
        return total
    return None


def _is_source_valid_empty_terminal(response: object) -> bool:
    """Genuine 0-card page 1: cursor.total==0 как source-valid terminal."""
    total = _parse_cursor_total(response)
    return total == 0


def _cursor_total_signals_terminal(response: object, page_limit: int) -> bool:
    """
    cursor.total (per-page count) < page_limit на полной странице — terminal hint.

    Malformed total не трактуется как terminal (fail-closed).
    """
    total = _parse_cursor_total(response)
    if total is None:
        return False
    return total < page_limit


def _request_cursor_fingerprint(
    body: PostContentV2GetCardsListBody,
) -> tuple[str, int] | None:
    """Fingerprint курсора запроса для loop detection."""
    settings = body.settings
    if isinstance(settings, Unset):
        return None
    cursor_obj = settings.cursor
    if isinstance(cursor_obj, Unset):
        return None
    updated_at_raw = cursor_obj.updated_at
    nm_id_raw = cursor_obj.nm_id
    if isinstance(updated_at_raw, Unset) or isinstance(nm_id_raw, Unset):
        return None
    if not _valid_updated_at(updated_at_raw):
        return None
    parsed_nm = _parse_positive_int(nm_id_raw)
    if parsed_nm is None:
        return None
    return (updated_at_raw, parsed_nm)


def _advance_body(
    *,
    body: PostContentV2GetCardsListBody,
    cards_list: list[PostContentV2GetCardsListResponse200CardsItem],
    response_cursor: object,
    page_limit: int,
) -> PostContentV2GetCardsListBody | None:
    settings = body.settings
    if isinstance(settings, Unset):
        return None
    filter_raw = settings.filter_
    sort_raw = settings.sort
    if isinstance(filter_raw, Unset) or isinstance(sort_raw, Unset):
        return None

    updated_at: str | None = None
    next_nm_id: int | None = None
    if not isinstance(response_cursor, Unset):
        resp_updated = getattr(response_cursor, "updated_at", UNSET)
        resp_nm = getattr(response_cursor, "nm_id", UNSET)
        if _valid_updated_at(resp_updated):
            updated_at = cast(str, resp_updated)
        parsed_resp_nm = _parse_positive_int(resp_nm)
        if parsed_resp_nm is not None:
            next_nm_id = parsed_resp_nm

    if updated_at is None or next_nm_id is None:
        if cards_list:
            last = cards_list[-1]
            last_updated = getattr(last, "updated_at", UNSET)
            last_nm = getattr(last, "nm_id", UNSET)
            if updated_at is None and _valid_updated_at(last_updated):
                updated_at = cast(str, last_updated)
            if next_nm_id is None:
                next_nm_id = _parse_positive_int(last_nm)
        if updated_at is None or next_nm_id is None:
            return None

    return _build_cards_list_body(
        page_limit=page_limit,
        updated_at=updated_at,
        nm_id=next_nm_id,
        filter_dict=filter_raw.to_dict(),
        sort_dict=sort_raw.to_dict(),
    )
