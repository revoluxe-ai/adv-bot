import json
from abc import ABC
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Self


@dataclass
class BaseDataHandler(ABC):
    dt: datetime

    def to_json(self) -> str:
        d = asdict(self)
        d["dt"] = self.dt.isoformat()  # сериализуем datetime в строку
        return json.dumps(d)

    @classmethod
    def from_json(cls, d: str) -> Self:
        data = json.loads(d)
        data["dt"] = datetime.fromisoformat(data["dt"])  # десериализуем обратно
        return cls(**data)
