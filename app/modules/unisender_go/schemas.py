from __future__ import annotations

from typing import Any

from pydantic import BaseModel, field_validator


class EmailRecipient(BaseModel):
    email: str
    substitutions: dict[str, str] | None = None
    metadata: dict[str, str] | None = None


class EmailBody(BaseModel):
    html: str | None = None
    plaintext: str | None = None
    amp: str | None = None


class TransactionalMessage(BaseModel):
    """Payload under the top-level ``message`` key for ``email/send.json``."""

    recipients: list[EmailRecipient]
    subject: str | None = None
    from_email: str | None = None
    reply_to: str | None = None
    body: EmailBody | None = None
    template_id: str | None = None
    tags: list[str] | None = None
    skip_unsubscribe: int | None = None
    global_language: str | None = None
    template_engine: str | None = None
    global_substitutions: dict[str, str] | None = None
    global_metadata: dict[str, Any] | None = None
    track_links: int | None = None
    track_read: int | None = None
    idempotence_key: str | None = None
    headers: dict[str, str] | None = None

    model_config = {"extra": "ignore"}


class EmailSendApiRequest(BaseModel):
    message: TransactionalMessage


class EmailSendResponse(BaseModel):
    """Successful transactional API response for ``email/send``."""

    status: str
    job_id: str | None = None
    emails: list[str] | None = None
    failed_emails: dict[str, str] | None = None

    @field_validator("status")
    @classmethod
    def status_is_success(cls, v: str) -> str:
        if v != "success":
            raise ValueError(f"expected status success, got {v!r}")
        return v


class EmailSendErrorBody(BaseModel):
    """Error JSON body from Unisender Go API."""

    status: str
    code: int | None = None
    message: str | None = None

    model_config = {"extra": "ignore"}
