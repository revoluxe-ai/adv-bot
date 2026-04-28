"""Real Unisender Go send; skipped unless API key and test recipient are set in the environment."""

from __future__ import annotations

import pytest

from app.modules.unisender_go import EmailBody, EmailRecipient, TransactionalMessage
from app.modules.unisender_go.client import UnisenderGoClient
from app.settings import settings

pytestmark = [pytest.mark.integration, pytest.mark.sandbox, pytest.mark.asyncio]


@pytest.mark.asyncio
async def test_send_transactional_email_real() -> None:
    if not settings.unisender_go_api_key:
        pytest.skip("UNISENDER_GO_API_KEY is not set")
    recipient = settings.unisender_go_integration_test_recipient
    if not recipient:
        pytest.skip("UNISENDER_GO_INTEGRATION_TEST_RECIPIENT is not set")

    default_from = settings.unisender_go_default_from_email
    if not default_from:
        pytest.skip(
            "UNISENDER_GO_DEFAULT_FROM_EMAIL is required for this integration test",
        )

    client = UnisenderGoClient.from_settings(settings)
    try:
        msg = TransactionalMessage(
            recipients=[EmailRecipient(email=recipient)],
            subject="adv-bot integration test",
            body=EmailBody(
                plaintext="This is an automated test message from adv-bot pytest.",
            ),
        )
        result = await client.send_email(msg)
        assert result.status == "success"
        assert result.job_id
    finally:
        await client.aclose()
