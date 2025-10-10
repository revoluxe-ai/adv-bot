"""Script to search a product position on Wildberries search results."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Iterable

try:  # noqa: SIM105 - keep compatibility with both run locations
    from set_path import add_project_root_to_path
except ImportError:  # pragma: no cover - fallback for executions from project root
    from scripts.set_path import add_project_root_to_path

add_project_root_to_path()

from aiogram.client.session import aiohttp  # type: ignore  # pragma: no cover

logger = logging.getLogger(__name__)


class TotalPages:
    """Helper class that mirrors the behaviour of the parser service."""

    def __init__(self) -> None:
        self._total_pages = 60

    @property
    def total_pages(self) -> int:
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value: int) -> None:
        if value > 60:
            value = 60
        if value < 0:
            value = 0
        self._total_pages = value


class DataError(Exception):
    """Generic data parsing error."""


def get_parse_url(text: str, page: int) -> str:
    assert 60 >= page > 0
    return (
        "https://search.wb.ru/exactmatch/ru/common/v5/search?ab_testing=false&"
        "appType=32&curr=rub&dest=-1257786&"
        f"page={page}&query={text}&resultset=catalog&sort=popular&"
        "suppressSpellcheck=false"
    )


@dataclass(slots=True)
class ProductPosition:
    """Representation of a product position on a particular page."""

    page: int
    position_on_page: int
    absolute_position: int
    nmid: int | None
    adv_id: int | None
    adv_type: int | None


async def _fetch_page(
    session: aiohttp.ClientSession, keyword: str, page: int
) -> tuple[list[dict], int | None]:
    """Fetch a search results page from Wildberries and return the data."""

    url = get_parse_url(keyword, page)
    logger.debug("Requesting page %s for keyword %s", page, keyword)
    async with session.get(url) as response:
        if response.status != 200:
            raise DataError(
                f"Unexpected status code {response.status} for page {page}", keyword
            )
        response_text = await response.text()

    if not response_text:
        raise DataError("Empty response from server", keyword)

    data = json.loads(response_text)

    if not data:
        logger.info("Received empty data for keyword %s on page %s", keyword, page)
        return [], None

    try:
        if data["payloadVersion"] != 2:
            raise DataError("Unsupported payload version", keyword)
    except KeyError as exc:  # pragma: no cover - unexpected format
        raise DataError("Missing payload version", keyword) from exc

    products = data.get("data", {}).get("products", [])
    total_items = data.get("data", {}).get("total")

    if not isinstance(products, list):
        raise DataError("Unexpected products format", keyword)

    if total_items is not None and not isinstance(total_items, int):
        logger.debug("Total items value has unexpected type: %s", type(total_items))
        total_items = None

    return products, total_items


def _iter_product_positions(
    products: list[dict], page: int
) -> Iterable[ProductPosition]:
    """Yield :class:`ProductPosition` objects for the given page."""

    first_position = (page - 1) * 100
    for index, product in enumerate(products, start=1):
        nmid = product.get("id")
        adv_data = product.get("log", {}) if isinstance(product, dict) else {}
        adv_id = adv_data.get("advertId") if isinstance(adv_data, dict) else None
        adv_type = adv_data.get("tp") if isinstance(adv_data, dict) else None

        # Normalize adv_type the same way as in parser service
        if adv_type == "c":
            normalized_type = 9
        elif adv_type == "b":
            normalized_type = 8
        elif isinstance(adv_type, int):
            raise DataError(f"Unknown advertisement type {adv_type}", str(nmid))
        else:
            normalized_type = None

        yield ProductPosition(
            page=page,
            position_on_page=index,
            absolute_position=first_position + index,
            nmid=nmid if isinstance(nmid, int) else None,
            adv_id=adv_id if isinstance(adv_id, int) else None,
            adv_type=normalized_type,
        )


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")


async def _find_positions(
    keyword: str,
    target_nmid: int | None,
    max_pages: int,
    stop_on_first: bool,
) -> list[ProductPosition]:
    total_pages = TotalPages()
    total_pages.total_pages = max_pages

    found_positions: list[ProductPosition] = []

    async with aiohttp.ClientSession() as session:
        page = 1
        while page <= total_pages.total_pages:
            try:
                products, total_items = await _fetch_page(session, keyword, page)
            except DataError as exc:
                logger.error("Failed to parse page %s: %s", page, exc)
                break
            except Exception as exc:  # pragma: no cover - network errors
                logger.exception("Unexpected error on page %s: %s", page, exc)
                break

            if total_items:
                max_page = (total_items + 99) // 100
                total_pages.total_pages = max_page

            if not products:
                logger.info("No products found on page %s", page)
                page += 1
                continue

            try:
                for product_position in _iter_product_positions(products, page):
                    if target_nmid is None or product_position.nmid == target_nmid:
                        found_positions.append(product_position)
                        logger.info(
                            "Found product %s on page %s (position %s, absolute %s)",
                            product_position.nmid,
                            product_position.page,
                            product_position.position_on_page,
                            product_position.absolute_position,
                        )
                        if stop_on_first and target_nmid is not None:
                            return found_positions
            except DataError as exc:
                logger.error("Error while processing products on page %s: %s", page, exc)
                break

            page += 1

    if not found_positions:
        logger.info("Product not found for keyword '%s'", keyword)

    return found_positions


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search Wildberries for a product by keyword and report its positions."
        )
    )
    parser.add_argument(
        "--keyword",
        "-k",
        required=True,
        help="Keyword to search on Wildberries",
    )
    parser.add_argument(
        "--nmid",
        type=int,
        help="Numeric identifier (NMID) of the product to locate. If omitted, all products will be listed.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=60,
        help="Maximum number of pages to scan (1-60)",
    )
    parser.add_argument(
        "--stop-on-first",
        action="store_true",
        help="Stop after the first occurrence of the target NMID",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    max_pages = max(1, min(60, args.max_pages))
    _setup_logging(args.verbose)

    positions = asyncio.run(
        _find_positions(args.keyword, args.nmid, max_pages, args.stop_on_first)
    )

    if not positions:
        return

    if args.nmid is None:
        print("\nSummary of found products:")
        for position in positions:
            print(
                f"NMID {position.nmid} -> page {position.page}, "
                f"position {position.position_on_page} (absolute {position.absolute_position})"
            )
    else:
        print("\nSummary of positions for NMID", args.nmid)
        for position in positions:
            print(
                f"Page {position.page}, position {position.position_on_page} "
                f"(absolute {position.absolute_position})"
            )


if __name__ == "__main__":
    main()
