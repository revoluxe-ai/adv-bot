from typing import Any

class PingManager:
    def __init__(self, wb_access: Any, session: Any):
        self.wb_access = wb_access
        self.session = session

    async def ping_analytics_rights_and_connect(self) -> bool:
        # Lightweight stub to replace legacy wb_api ping manager
        return True
