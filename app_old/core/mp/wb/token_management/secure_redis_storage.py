from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Dict, Optional, Set


@dataclass
class TokenState:
    token_id: str
    is_bad: bool = False
    success_count: int = 0
    error_count: int = 0


@dataclass
class ShopState:
    # tokens -> method_name -> { token_id -> TokenState }
    tokens: Dict[str, Dict[str, TokenState]]

    def __init__(self):
        self.tokens = {}


class SecureRedisTokenStorage:
    """In-memory mock storage to replace Redis-backed storage for tests.

    Provides the minimal API used by EnhancedShopTokenManager.
    """

    def __init__(self):
        self._shop_states: Dict[str, ShopState] = {}
        self._lock = asyncio.Lock()

    async def get_bad_tokens(self, shop_id: str, method_name: str) -> Set[str]:
        async with self._lock:
            shop = self._shop_states.get(shop_id, ShopState())
            method_tokens = shop.tokens.get(method_name, {})
            return {tok.token_id for tok in method_tokens.values() if tok.is_bad}

    async def mark_token_bad(self, shop_id: str, method_name: str, token_id: str, error_message: str) -> None:
        async with self._lock:
            shop = self._shop_states.get(shop_id)
            if shop is None:
                shop = ShopState()
                self._shop_states[shop_id] = shop
            method_tokens = shop.tokens.setdefault(method_name, {})
            token = method_tokens.get(token_id)
            if token is None:
                token = TokenState(token_id=token_id, is_bad=True)
                method_tokens[token_id] = token
            else:
                token.is_bad = True

    async def mark_token_success(self, shop_id: str, method_name: str, token_id: str) -> None:
        async with self._lock:
            shop = self._shop_states.setdefault(shop_id, ShopState())
            method_tokens = shop.tokens.setdefault(method_name, {})
            token = method_tokens.get(token_id)
            if token is None:
                token = TokenState(token_id=token_id, is_bad=False, success_count=1)
                method_tokens[token_id] = token
            else:
                token.is_bad = False
                token.success_count += 1

    async def get_shop_state(self, shop_id: str) -> Optional[ShopState]:
        # Return a copy-like object; for simplicity return the stored one or a fresh empty state
        async with self._lock:
            return self._shop_states.get(shop_id, ShopState())

    async def clear_shop_state(self, shop_id: str) -> None:
        async with self._lock:
            self._shop_states[shop_id] = ShopState()


