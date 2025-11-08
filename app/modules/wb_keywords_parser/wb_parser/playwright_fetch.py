from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import quote_plus

from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

logger = logging.getLogger(__name__)


def resolve_profile_dir(base_dir: str | None, keyword: str) -> str | None:
    """Create a deterministic profile directory for the given keyword."""

    if not base_dir:
        return None

    digest = hashlib.sha256(keyword.encode("utf-8")).hexdigest()
    path = Path(base_dir) / digest
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _extract_search_payload(
    data: dict[str, Any], keyword: str
) -> tuple[list[dict], str | None, int | None, int | None]:
    if not data:
        return [], None, None, None

    payload_version = data.get("payloadVersion")
    if payload_version != 2:
        raise RuntimeError(f"Unexpected payload version: {payload_version!r}")

    metadata = data.get("metadata") or {}
    catalog_type = metadata.get("catalog_type")

    if catalog_type == "merger":
        cluster = keyword
        preset = hash(keyword)
    else:
        catalog_value = metadata.get("catalog_value", "")
        match = re.search(r"preset=(\d+)", catalog_value)
        if not match:
            raise RuntimeError("preset is missing in catalog_value")
        preset = int(match.group(1))
        cluster = metadata.get("normquery")

    total_items = data.get("data", {}).get("total")
    products = data.get("data", {}).get("products") or []

    if cluster is None:
        raise RuntimeError("cluster is missing in metadata")

    return products, cluster, preset, total_items


def _build_search_url(query: str, page: int) -> str:
    encoded_query = quote_plus(query)
    return (
        "https://www.wildberries.ru/catalog/0/search.aspx"
        f"?search={encoded_query}&sort=popular&page={page}"
    )


async def _setup_context(
    *,
    headless: bool,
    profile_dir: str | None,
    proxy_url: str | None,
) -> tuple[BrowserContext, Callable[[], Awaitable[None]]]:
    proxy = {"server": proxy_url} if proxy_url else None

    playwright = await async_playwright().start()
    viewport = {"width": 1280, "height": 900}
    browser = None

    try:
        if profile_dir:
            context = await playwright.chromium.launch_persistent_context(
                profile_dir,
                headless=headless,
                proxy=proxy,
                viewport=viewport,
            )
        else:
            browser = await playwright.chromium.launch(
                headless=headless,
                proxy=proxy,
            )
            context = await browser.new_context(viewport=viewport)

        await context.set_extra_http_headers(
            {
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

        async def _close() -> None:
            try:
                await context.close()
            finally:
                if browser is not None:
                    await browser.close()
                await playwright.stop()

        async def _close_factory() -> None:
            await _close()

        return context, _close_factory
    except Exception:
        await playwright.stop()
        raise


async def _close_context(
    close_factory: Callable[[], Awaitable[None]]
) -> None:
    await close_factory()


async def fetch_wb_search(
    text: str,
    page: int,
    *,
    timeout_sec: float = 12.0,
    headless: bool = True,
    profile_dir: str | None = None,
    proxy_url: str | None = None,
) -> tuple[list[dict], str | None, int | None, int | None]:
    """Fetch WB search results for the given query and page."""

    context, close_factory = await _setup_context(
        headless=headless, profile_dir=profile_dir, proxy_url=proxy_url
    )

    try:
        page_obj: Page
        if context.pages:
            page_obj = context.pages[0]
        else:
            page_obj = await context.new_page()

        loop = asyncio.get_running_loop()
        payload_future: asyncio.Future[dict[str, Any]] = loop.create_future()

        async def _capture_response(response) -> None:  # type: ignore[no-untyped-def]
            if payload_future.done():
                return
            url = response.url
            if "/exactmatch/ru/common/v5/search" not in url:
                return
            if f"page={page}" not in url:
                return
            try:
                data = await response.json()
            except Exception as exc:  # noqa: BLE001
                if not payload_future.done():
                    payload_future.set_exception(exc)
                return

            if not payload_future.done():
                payload_future.set_result(data)

        context.on("response", _capture_response)

        target_url = _build_search_url(text, page)

        try:
            await page_obj.goto(
                target_url,
                wait_until="domcontentloaded",
                timeout=timeout_sec * 1000,
            )
        except PlaywrightTimeoutError as exc:
            raise RuntimeError(
                f"WB search page load timeout for '{text}' page {page}"
            ) from exc

        await page_obj.wait_for_timeout(random.randint(300, 600))
        await page_obj.mouse.move(
            random.randint(100, 600), random.randint(100, 700)
        )
        await page_obj.wait_for_timeout(random.randint(150, 300))

        for _ in range(random.randint(1, 3)):
            await page_obj.mouse.wheel(0, random.randint(200, 600))
            await page_obj.wait_for_timeout(random.randint(200, 400))

        try:
            payload = await asyncio.wait_for(
                payload_future, timeout=timeout_sec
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError(
                f"WB search JSON timeout for '{text}' page {page}"
            ) from exc

        products, cluster, preset, total_items = _extract_search_payload(
            payload, text
        )
        return products, cluster, preset, total_items
    finally:
        try:
            await _close_context(close_factory)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to close Playwright context: %s", exc)
