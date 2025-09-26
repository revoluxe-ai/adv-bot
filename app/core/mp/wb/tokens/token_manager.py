from __future__ import annotations

import asyncio
from typing import Dict, Set, Optional, List

# For now, we'll use a simple in-memory store for tokens.
# In a real-world scenario, this would interact with a database or external service.
_TOKEN_STORAGE: Dict[str, List[str]] = {
    "test_shop": ["token_shop_1_promotion_1", "token_shop_1_promotion_2"],
    "shop_abc": ["token_abc_promo_1", "token_abc_promo_2"],
}


class TokenManager:
    """Manages API tokens for a specific shop_id, handling invalidation per API section."""

    def __init__(self, shop_id: str) -> None:
        self._shop_id = shop_id
        self._tokens: List[str] = _TOKEN_STORAGE.get(shop_id, [])
        # Stores tokens marked as invalid for a specific section
        self._invalid_tokens_by_section: Dict[str, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def get_token(self, section: str) -> str:
        """Returns a valid token for the given section, considering invalidations."""
        async with self._lock:
            invalid_for_section = self._invalid_tokens_by_section.get(section, set())
            for token in self._tokens:
                if token not in invalid_for_section:
                    return token
            # If all tokens are invalid for this section, clear invalidation and retry (or raise error)
            self._invalid_tokens_by_section[section] = set()
            if self._tokens:
                return self._tokens[0] # Return first token after reset
            raise ValueError(f"No valid tokens available for shop {self._shop_id} and section {section}")

    async def mark_invalid(self, section: str, token: Optional[str] = None) -> None:
        """Marks a token as invalid for the specified section and initiates selection of a new one."""
        async with self._lock:
            if section not in self._invalid_tokens_by_section:
                self._invalid_tokens_by_section[section] = set()

            if token:
                self._invalid_tokens_by_section[section].add(token)
            # In a real scenario, this would also trigger a token refresh/re-evaluation logic


class TokenManagerFactory:
    """Factory/registry for TokenManager instances per shop (singleton per shop via DI)."""

    def __init__(self) -> None:
        self._managers: Dict[str, TokenManager] = {}

    def get_manager(self, shop_id: str) -> TokenManager:
        if shop_id not in self._managers:
            self._managers[shop_id] = TokenManager(shop_id=shop_id)
        return self._managers[shop_id]
