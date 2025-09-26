from app.core.mp.wb.adapters.promotion_v1_adapter import PromotionV1Adapter


class WBBaseAdapters:
    
    def __init__(self):
        self._auth_client_factory = AuthClientFactory()
        self._rate_limiter = RateLimiter()
