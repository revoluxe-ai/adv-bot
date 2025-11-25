from dataclasses import dataclass
from datetime import date


@dataclass
class GetKeywordPositionsCommand:
    nmid: int
    start: date
    end: date
    texts: list[str]
