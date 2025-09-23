from dataclasses import dataclass
from datetime import datetime

from ..base_data_handler import BaseDataHandler


@dataclass
class Success(BaseDataHandler):
    dt: datetime
