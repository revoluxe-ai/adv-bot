"""Integration tests for SSR web registration."""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.utils.db.models import User
from app.web.passwords import verify_password
from app.web.registration_service import register_web_user
from app.web.routes.auth import get_db_session, router


def _make_test_app(async_engine) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    async def _session_override():
        sm = async_sessionmaker(async_engine, expire_on_commit=False)
        async with sm() as session:
            yield session

    app.dependency_overrides[get_db_session] = _session_override
    return app


@pytest.mark.integration
async def test_register_page_renders(async_engine) -> None:
    app = _make_test_app(async_engine)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/register")
    assert resp.status_code == 200
    assert "Регистрация" in resp.text
    assert "htmx.org" in resp.text


@pytest.mark.integration
async def test_register_success_and_duplicate(async_engine) -> None:
    email = f"u_{uuid.uuid4().hex}@example.com"
    app = _make_test_app(async_engine)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp_ok = await client.post(
            "/register",
            data={
                "email": email,
                "password": "secretsecret",
                "password_confirm": "secretsecret",
            },
        )
        resp_dup = await client.post(
            "/register",
            data={
                "email": email,
                "password": "secretsecret",
                "password_confirm": "secretsecret",
            },
        )

    assert resp_ok.status_code == 200
    assert "успеш" in resp_ok.text.lower()

    assert resp_dup.status_code == 200
    assert "уже" in resp_dup.text.lower()

    sm = async_sessionmaker(async_engine, expire_on_commit=False)
    async with sm() as session:
        row = await session.scalar(select(User).where(User.email == email))
        assert row is not None
        assert row.password_hash is not None
        assert verify_password("secretsecret", row.password_hash)
        assert row.user_telegram_id < 0
        await session.execute(delete(User).where(User.email == email))
        await session.commit()


@pytest.mark.integration
async def test_register_password_mismatch(async_engine) -> None:
    app = _make_test_app(async_engine)
    email = f"m_{uuid.uuid4().hex}@example.com"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/register",
            data={
                "email": email,
                "password": "secretsecret",
                "password_confirm": "othersecret",
            },
        )
    assert resp.status_code == 200
    assert "не совпадают" in resp.text.lower()


@pytest.mark.integration
async def test_register_web_user_service(async_engine) -> None:
    email = f"s_{uuid.uuid4().hex}@example.com"
    sm = async_sessionmaker(async_engine, expire_on_commit=False)
    async with sm() as session:
        user = await register_web_user(session, email, "longpassword")
        uid = user.id

    async with sm() as session:
        loaded = await session.get(User, uid)
        assert loaded is not None
        assert loaded.email == email
        assert verify_password("longpassword", loaded.password_hash or "")
        await session.execute(delete(User).where(User.id == uid))
        await session.commit()
