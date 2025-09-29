import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, List, Dict, Any

from app.modules.common_slaves.wildberries.models import WBToken
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from .secure_redis_storage import SecureRedisTokenStorage

logger = logging.getLogger(__name__)


@dataclass
class TokenScore:
    token_id: str
    score: float
    is_expired: bool
    is_bad: bool
    success_rate: float
    days_until_expiry: int


class EnhancedShopTokenManager:
    def __init__(
        self,
        wb_access: WBCabinetAccess,
        storage: Optional[SecureRedisTokenStorage] = None,
    ):
        self.wb_access = wb_access
        self.shop_id = wb_access.shop_id
        self._storage = storage or SecureRedisTokenStorage()

        self._tokens = sorted(wb_access.tokens, key=lambda x: x.expires, reverse=True)
        self._current_tokens: Dict[str, Optional[WBToken]] = {}
        self._lock = asyncio.Lock()

        self._scoring_weights = {
            "success_rate": 0.4,
            "freshness": 0.3,
            "error_penalty": 0.2,
            "usage_bonus": 0.1,
        }

    async def get_best_token(self, method_name: str) -> Optional[WBToken]:
        async with self._lock:
            current = self._current_tokens.get(method_name)
            if current and await self._is_token_usable(current, method_name):
                return current

            best_token = await self._select_best_token(method_name)
            if best_token:
                self._current_tokens[method_name] = best_token
                logger.debug(
                    f"Selected token {best_token.id} for method {method_name} in shop {self.shop_id}"
                )

            return best_token

    async def _select_best_token(self, method_name: str) -> Optional[WBToken]:
        if not self._tokens:
            return None

        bad_tokens = await self._storage.get_bad_tokens(self.shop_id, method_name)
        shop_state = await self._storage.get_shop_state(self.shop_id)

        token_scores: List[TokenScore] = []
        for token in self._tokens:
            score = await self._calculate_token_score(
                token, method_name, bad_tokens, shop_state
            )
            token_scores.append(score)

        usable_scores = [s for s in token_scores if not s.is_expired and not s.is_bad]
        if not usable_scores:
            logger.warning(
                f"No usable tokens for method {method_name} in shop {self.shop_id}"
            )
            return None

        usable_scores.sort(key=lambda x: x.score, reverse=True)
        best_score = usable_scores[0]
        best_token = next(
            (t for t in self._tokens if str(t.id) == best_score.token_id), None
        )

        logger.debug(
            f"Token scoring for {method_name}: best token {best_score.token_id} with score {best_score.score:.3f}"
        )
        return best_token

    async def _calculate_token_score(
        self, token: WBToken, method_name: str, bad_tokens: Set[str], shop_state: Any
    ) -> TokenScore:
        token_id = str(token.id)
        is_bad = token_id in bad_tokens
        is_expired = token.is_expired

        token_state = None
        if (
            shop_state
            and method_name in shop_state.tokens
            and token_id in shop_state.tokens[method_name]
        ):
            token_state = shop_state.tokens[method_name][token_id]

        success_count = token_state.success_count if token_state else 0
        error_count = token_state.error_count if token_state else 0
        total_requests = success_count + error_count

        success_rate = success_count / total_requests if total_requests > 0 else 1.0

        days_until_expiry = (token.expires - datetime.utcnow()).days
        freshness = min(days_until_expiry / 365, 1.0) if days_until_expiry > 0 else 0.0

        error_penalty = min(error_count * 0.1, 1.0)
        usage_bonus = min(total_requests * 0.01, 0.5)

        if is_expired or is_bad:
            score = 0.0
        else:
            score = (
                success_rate * self._scoring_weights["success_rate"]
                + freshness * self._scoring_weights["freshness"]
                + usage_bonus * self._scoring_weights["usage_bonus"]
                - error_penalty * self._scoring_weights["error_penalty"]
            )

        return TokenScore(
            token_id=token_id,
            score=max(score, 0.0),
            is_expired=is_expired,
            is_bad=is_bad,
            success_rate=success_rate,
            days_until_expiry=days_until_expiry,
        )

    async def _is_token_usable(self, token: WBToken, method_name: str) -> bool:
        if token.is_expired():
            return False
        bad_tokens = await self._storage.get_bad_tokens(self.shop_id, method_name)
        return str(token.id) not in bad_tokens

    async def mark_token_bad(
        self, method_name: str, token_id: str, error_message: str
    ) -> None:
        async with self._lock:
            await self._storage.mark_token_bad(
                self.shop_id, method_name, str(token_id), error_message
            )
            if method_name in self._current_tokens:
                current = self._current_tokens[method_name]
                if current and str(current.id) == str(token_id):
                    self._current_tokens[method_name] = None

            logger.warning(
                f"Marked token {token_id} as bad for method {method_name} in shop {self.shop_id}: {error_message}"
            )

    async def mark_token_success(self, method_name: str, token_id: str) -> None:
        await self._storage.mark_token_success(self.shop_id, method_name, str(token_id))

    async def get_token_statistics(self, method_name: str) -> Dict[str, Any]:
        shop_state = await self._storage.get_shop_state(self.shop_id)
        if not shop_state or method_name not in shop_state.tokens:
            return {
                "total_tokens": len(self._tokens),
                "bad_tokens": 0,
                "usable_tokens": len(self._tokens),
            }

        method_tokens = shop_state.tokens[method_name]
        bad_count = sum(1 for state in method_tokens.values() if state.is_bad)
        total_requests = sum(
            state.success_count + state.error_count for state in method_tokens.values()
        )

        return {
            "total_tokens": len(self._tokens),
            "bad_tokens": bad_count,
            "usable_tokens": len(self._tokens) - bad_count,
            "total_requests": total_requests,
            "method_tokens_tracked": len(method_tokens),
        }

    async def refresh_tokens(self, new_wb_access: WBCabinetAccess) -> None:
        async with self._lock:
            self.wb_access = new_wb_access
            self._tokens = sorted(
                new_wb_access.tokens, key=lambda x: x.expires, reverse=True
            )
            self._current_tokens.clear()
            await self._storage.clear_shop_state(self.shop_id)
            logger.info(f"Refreshed {len(self._tokens)} tokens for shop {self.shop_id}")

    @property
    def current_token(self) -> Optional[WBToken]:
        if self._tokens:
            return self._tokens[0]
        return None
