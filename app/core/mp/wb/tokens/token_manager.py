from __future__ import annotations

from typing import Dict, List, Optional


class TokenManager:
    """Manage tokens for a single shop. Tracks tokens and per-section invalid marks."""

    def __init__(self, shop_id: str, tokens: Optional[List[str]] = None) -> None:
        self.shop_id = shop_id
        self._tokens: List[str] = tokens or []
        # section -> set of invalid token indices
        self._invalid_by_section: Dict[str, set[int]] = {}
        self._current_index: int = 0

    async def get_token(self, section: str) -> str:
        """Return a valid token for the given section, considering invalid marks.

        Searches the token list starting from the current pointer and returns the
        first token index that is not marked invalid for the given section. If no
        token is available raises RuntimeError.
        """
        if not self._tokens:
            raise RuntimeError("no tokens configured for shop")

        invalid = self._invalid_by_section.get(section, set())
        n = len(self._tokens)
        # try all tokens starting from current_index
        for offset in range(n):
            idx = (self._current_index + offset) % n
            if idx in invalid:
                continue
            # move current pointer to found index
            self._current_index = idx
            return self._tokens[idx]

        raise RuntimeError(f"no valid token available for section {section}")

    def mark_invalid(self, section: str, token: Optional[str] = None) -> None:
        """Mark provided token (or current) as invalid for a section and advance selection.

        If token is provided, mark that token instance as invalid (first matching
        index). Otherwise mark the current token.
        After marking, advance the current index to the next candidate (if any).
        """
        if not self._tokens:
            return

        # determine index to mark
        idx_to_mark: Optional[int] = None
        if token is not None:
            try:
                idx_to_mark = self._tokens.index(token)
            except ValueError:
                # token not found - nothing to mark
                return
        else:
            idx_to_mark = self._current_index

        invalid_set = self._invalid_by_section.setdefault(section, set())
        invalid_set.add(idx_to_mark)

        # advance current_index to next not-marked index (relative to current)
        n = len(self._tokens)
        for offset in range(1, n + 1):
            next_idx = (idx_to_mark + offset) % n
            if next_idx not in invalid_set:
                self._current_index = next_idx
                return
        # all tokens marked invalid for this section -> keep pointer unchanged


class TokenManagerFactory:
    """Factory/registry for TokenManager instances per shop (singleton per shop via DI)."""

    def __init__(self) -> None:
        self._managers: Dict[str, TokenManager] = {}

    def get_manager(self, shop_id: str) -> TokenManager:
        if shop_id not in self._managers:
            self._managers[shop_id] = TokenManager(shop_id=shop_id)
        return self._managers[shop_id]
