"""DTO for campaign activity reason stored in Redis."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
    AuctionReasonCode,
    AutoReasonCode,
    CampaignActivityCommand,
    parse_reason_code,
)

if TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.services.redis_campaign_activity_reason_manager.enums import (
        CampaignReasonCode,
    )


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class CampaignActivityReason:
    """Last command and reason from the activity module for one campaign (auto or search)."""

    __slots__ = ("command", "reason_code", "updated_at")

    def __init__(
        self,
        command: CampaignActivityCommand,
        reason_code: AutoReasonCode | AuctionReasonCode,
        updated_at: datetime | None = None,
    ) -> None:
        self.command = command
        self.reason_code: CampaignReasonCode = reason_code
        self.updated_at = updated_at if updated_at is not None else _now_utc()

    def to_redis(self) -> str:
        """Serialize to JSON string for Redis. Enum fields stored as .value."""
        payload = {
            "command": self.command.value,
            "reason_code": self.reason_code.value,
            "updated_at": self.updated_at.isoformat(),
        }
        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def from_redis(cls, raw: str) -> CampaignActivityReason | None:
        """Deserialize from JSON string from Redis. Returns None if invalid."""
        try:
            data = json.loads(raw)
            cmd_val = data.get("command")
            reason_val = data.get("reason_code")
            updated_val = data.get("updated_at")
            if not cmd_val or not reason_val:
                return None
            command = CampaignActivityCommand(cmd_val)
            reason_code = parse_reason_code(reason_val)
            if reason_code is None:
                return None
            updated_at = (
                datetime.fromisoformat(updated_val.replace("Z", "+00:00"))
                if updated_val
                else _now_utc()
            )
            return cls(command=command, reason_code=reason_code, updated_at=updated_at)
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
