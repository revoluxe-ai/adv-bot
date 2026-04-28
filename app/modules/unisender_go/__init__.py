from __future__ import annotations

from app.modules.unisender_go.client import UnisenderGoClient
from app.modules.unisender_go.exceptions import UnisenderGoError
from app.modules.unisender_go.schemas import (
    EmailBody,
    EmailRecipient,
    EmailSendResponse,
    TransactionalMessage,
)

__all__ = [
    "EmailBody",
    "EmailRecipient",
    "EmailSendResponse",
    "TransactionalMessage",
    "UnisenderGoClient",
    "UnisenderGoError",
]
