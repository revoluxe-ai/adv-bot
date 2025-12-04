from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, Field


class Position(BaseModel):
    text: str
    datetime: date = Field(alias="date")
    position: float = Field(alias="avr_pos")

    model_config = {"populate_by_name": True}

@dataclass
class KeywordPositions:
    text: str
    positions: list[Position]

    @property
    def max_position(self) -> float:
        all_positions: list[float] = []
        for position in self.positions:
            all_positions.append(position.position)
        return min(all_positions)

class PositionHistory(BaseModel):
    nmid: int
    positions: list[Position]

    @property
    def keyword_positions(self)-> list[KeywordPositions]:
        text_to_positions: dict[str, list[Position]] = defaultdict(list)
        for position in self.positions:
            text_to_positions[position.text].append(position)

        keyword_positions: list[KeywordPositions] = []
        for text, positions in text_to_positions.items():
            keyword_position = KeywordPositions(text=text, positions=positions)
            keyword_positions.append(keyword_position)
        return keyword_positions
