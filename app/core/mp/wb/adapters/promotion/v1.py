from __future__ import annotations

from typing import Any, Dict, List
import json

import httpx

from app.core.mp.wb.adapters.base import BaseAdapter, AuthenticatedClient
from app.core.mp.wb.decorators.auth import auth_decorator
from app.core.mp.wb.decorators.rate_limit import rate_limit_decorator
from app.core.mp.wb.decorators.retry import retry_decorator


class PromotionV1Adapter((BaseAdapter):
    base_url = "https://advert-api.wildberries.ru/"

    def __init__(self):
        self.limiter = Limiter()

    @auth_decorator
    @rate_limit_decorator
    @retry_decorator
    async def get_min_bids(self, adv_id: int, nmids: List[int]) -> Dict[int, int]:



