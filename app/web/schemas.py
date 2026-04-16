"""Pydantic schemas for web registration."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class RegistrationForm(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    password_confirm: str = Field(min_length=8, max_length=256)
