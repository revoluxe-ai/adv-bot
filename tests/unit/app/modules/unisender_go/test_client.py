from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.modules.unisender_go import (
    EmailBody,
    EmailRecipient,
    TransactionalMessage,
    UnisenderGoClient,
    UnisenderGoError,
)


@pytest.mark.asyncio
async def test_send_email_success_parses_job_id() -> None:
    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(
        return_value=httpx.Response(
            200,
            json={
                "status": "success",
                "job_id": "1ZymBc-00041N-9X",
                "emails": ["user@example.com"],
            },
        )
    )
    client = UnisenderGoClient(
        "test-api-key",
        base_url="https://goapi.unisender.ru/ru/transactional/api/v1",
        http_client=mock_http,
    )
    msg = TransactionalMessage(
        recipients=[EmailRecipient(email="user@example.com")],
        subject="Hi",
        from_email="sender@example.com",
        body=EmailBody(plaintext="Hello"),
    )
    result = await client.send_email(msg)
    assert result.job_id == "1ZymBc-00041N-9X"
    assert result.emails == ["user@example.com"]
    mock_http.post.assert_awaited_once()
    call = mock_http.post.await_args
    assert call is not None
    assert (
        call.args[0]
        == "https://goapi.unisender.ru/ru/transactional/api/v1/email/send.json"
    )
    assert call.kwargs["headers"]["X-API-KEY"] == "test-api-key"
    body = call.kwargs["json"]
    assert body["message"]["from_email"] == "sender@example.com"
    await client.aclose()


@pytest.mark.asyncio
async def test_send_email_api_error_json_in_body() -> None:
    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(
        return_value=httpx.Response(
            200,
            json={
                "status": "error",
                "code": 150,
                "message": "invalid request",
            },
        )
    )
    client = UnisenderGoClient("key", http_client=mock_http)
    msg = TransactionalMessage(
        recipients=[EmailRecipient(email="a@b.com")],
        from_email="x@y.com",
        body=EmailBody(html="<p>x</p>"),
    )
    with pytest.raises(UnisenderGoError) as ei:
        await client.send_email(msg)
    assert ei.value.api_code == 150
    await client.aclose()


@pytest.mark.asyncio
async def test_send_email_http_error_parses_error_json() -> None:
    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(
        return_value=httpx.Response(
            400,
            text='{"status":"error","code":400,"message":"bad"}',
        )
    )
    client = UnisenderGoClient("key", http_client=mock_http)
    msg = TransactionalMessage(
        recipients=[EmailRecipient(email="a@b.com")],
        from_email="x@y.com",
        body=EmailBody(html="<p>x</p>"),
    )
    with pytest.raises(UnisenderGoError) as ei:
        await client.send_email(msg)
    assert ei.value.status_code == 400
    assert ei.value.api_code == 400
    await client.aclose()


@pytest.mark.asyncio
async def test_default_from_email_applied() -> None:
    mock_http = MagicMock(spec=httpx.AsyncClient)
    mock_http.post = AsyncMock(
        return_value=httpx.Response(
            200,
            json={"status": "success", "job_id": "j1"},
        )
    )
    client = UnisenderGoClient(
        "key",
        default_from_email="default@example.com",
        http_client=mock_http,
    )
    msg = TransactionalMessage(
        recipients=[EmailRecipient(email="u@example.com")],
        body=EmailBody(plaintext="t"),
    )
    await client.send_email(msg)
    call = mock_http.post.await_args
    assert call is not None
    assert call.kwargs["json"]["message"]["from_email"] == "default@example.com"
    await client.aclose()
