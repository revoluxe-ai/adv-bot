from dataclasses import dataclass
import datetime

@dataclass
class GetNormqueryStatsCommand:
    advert_id: int
    date_from: datetime.date
    date_to: datetime.date
    nmid: int
