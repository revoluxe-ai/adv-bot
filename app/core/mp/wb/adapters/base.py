from __future__ import annotations


class BaseAdapter:
    def __init__(self, shop_id: str) -> None:
        self.shop_id = shop_id
