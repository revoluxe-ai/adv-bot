"""SSR registration routes (Jinja + HTMX)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.db.session_maker import get_async_session_maker
from app.web.registration_service import EmailAlreadyRegisteredError, register_web_user
from app.web.schemas import RegistrationForm

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["web-auth"])


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_async_session_maker(read_only=False) as session:
        yield session


def _format_validation_errors(exc: ValidationError) -> list[str]:
    messages: list[str] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = str(loc[-1]) if loc else "form"
        msg = err.get("msg", "Invalid value")
        if field == "email":
            messages.append("Некорректный email")
        elif field in ("password", "password_confirm"):
            messages.append("Пароль должен быть от 8 до 256 символов")
        else:
            messages.append(f"{field}: {msg}")
    return messages or ["Некорректные данные формы"]


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={},
    )


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> HTMLResponse:
    try:
        data = RegistrationForm(
            email=email,
            password=password,
            password_confirm=password_confirm,
        )
    except ValidationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="partials/register_result.html",
            context={
                "errors": _format_validation_errors(exc),
                "success": False,
            },
            status_code=status.HTTP_200_OK,
        )

    if data.password != data.password_confirm:
        return templates.TemplateResponse(
            request=request,
            name="partials/register_result.html",
            context={
                "errors": ["Пароли не совпадают"],
                "success": False,
            },
            status_code=status.HTTP_200_OK,
        )

    try:
        await register_web_user(session, data.email, data.password)
    except EmailAlreadyRegisteredError:
        return templates.TemplateResponse(
            request=request,
            name="partials/register_result.html",
            context={
                "errors": ["Этот email уже зарегистрирован"],
                "success": False,
            },
            status_code=status.HTTP_200_OK,
        )

    return templates.TemplateResponse(
        request=request,
        name="partials/register_result.html",
        context={"errors": [], "success": True},
        status_code=status.HTTP_200_OK,
    )
