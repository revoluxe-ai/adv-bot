from dataclasses import dataclass
from datetime import datetime

from app.modules.shop_status_controle_manager.redis_manager.base_data_handler import (
    BaseDataHandler,
)


@dataclass
class Error(BaseDataHandler):
    dt: datetime
    type_error: str
    message_error: str
