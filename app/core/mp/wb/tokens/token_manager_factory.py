from __future__ import annotations

from typing import Dict

from app.core.mp.wb.tokens.token_manager import TokenManager


class TokenManagerFactory:
    """Factory that creates and caches TokenManager instances per shop_id."""

    def __init__(self) -> None:
        self._managers_cache: Dict[str, TokenManager] = {}

    def get_manager(self, shop_id: str) -> TokenManager:
        if shop_id not in self._managers_cache:
            self._managers_cache[shop_id] = TokenManager(shop_id)
        return self._managers_cache[shop_id]


def get_token_manager_factory() -> TokenManagerFactory:
    """Singleton accessor for TokenManagerFactory. Will be replaced by DI wiring."""
    # This function will be replaced by DI container wiring
    return TokenManagerFactory()
