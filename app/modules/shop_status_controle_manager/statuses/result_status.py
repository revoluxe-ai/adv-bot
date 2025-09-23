from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass
class Status:
    result: Literal["success", "error"]
    last_update: datetime
    last_error: Exception | None
