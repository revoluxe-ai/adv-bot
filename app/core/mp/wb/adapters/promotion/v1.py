from __future__ import annotations

from typing import Any, Dict, List
import json

import httpx

from app.core.mp.wb.adapters.base import BaseAdapter, AuthenticatedClient
from app.core.mp.wb.decorators.auth import auth_decorator
from app.core.mp.wb.decorators.rate_limit import rate_limit_decorator
from app.core.mp.wb.decorators.retry import retry_decorator


class PromotionV1Adapter(BaseAdapter):
    """Adapter for Promotion API v1. Stateful and scoped by shop_id/section/version."""

    def __init__(self, shop_id: str, version: str) -> None:
        super().__init__(shop_id=shop_id, section="promotion", version=version)
        # raw method names used for rate-limit keys
        self._raw_method_get_min_bids = "post_adv_v0_bids_min"
        self._raw_method_get_current_bids = "get_adv_v0_auction_adverts"
        self._raw_method_update_bids = "patch_adv_v0_bids"

    @auth_decorator
    @rate_limit_decorator
    @retry_decorator
    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return minimal bids mapping by nmid.

        Calls POST /adv/v0/bids/min with JSON payload {"advId": adv_id, "nmIds": nmids}
        and returns mapping nmid->minBid.
        """
        client: AuthenticatedClient = getattr(self, "_authenticated_client")
        url = f"{client.base_url}adv/v0/bids/min"
        payload = {"advId": adv_id, "nmIds": nmids}

        # use underlying session for transport
        session = getattr(client, "session", None)
        if session is None:
            raise RuntimeError("no http session attached to authenticated client")

        resp = await session.post(url, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"get_min_bids failed: {resp.status_code}")
        data = resp.json()
        # expecting mapping in response
        return {int(k): int(v) for k, v in data.items()}

    @auth_decorator
    @rate_limit_decorator
    @retry_decorator
    async def get_current_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:
        """Return current bids mapping by nmid.

        Calls GET /adv/v0/auction/adverts with query params advId and nmIds.
        """
        client: AuthenticatedClient = getattr(self, "_authenticated_client")
        base = client.base_url.rstrip("/")
        url = f"{base}/adv/v0/auction/adverts"
        params = {"advId": adv_id, "nmIds": ",".join(str(x) for x in nmids)}

        session = getattr(client, "session", None)
        if session is None:
            raise RuntimeError("no http session attached to authenticated client")

        resp = await session.get(url, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"get_current_bids failed: {resp.status_code}")
        data = resp.json()
        return {int(item["nmid"]): int(item["bid"]) for item in data}

    @auth_decorator
    @rate_limit_decorator
    @retry_decorator
    async def update_bids(self, payload: Any) -> None:
        """Send bids update batch via PATCH /adv/v0/bids"""
        client: AuthenticatedClient = getattr(self, "_authenticated_client")
        url = f"{client.base_url}adv/v0/bids"
        session = getattr(client, "session", None)
        if session is None:
            raise RuntimeError("no http session attached to authenticated client")

        resp = await session.patch(url, json=payload)
        if resp.status_code not in (200, 204):
            raise RuntimeError(f"update_bids failed: {resp.status_code}")
        return None
