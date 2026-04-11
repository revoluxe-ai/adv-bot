"""Unit tests for registration Pydantic schema."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.web.schemas import RegistrationForm


@pytest.mark.unit
def test_registration_form_valid() -> None:
    m = RegistrationForm(
        email="user@example.com",
        password="longenough",
        password_confirm="longenough",
    )
    assert m.email == "user@example.com"


@pytest.mark.unit
def test_registration_form_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegistrationForm(
            email="user@example.com",
            password="short",
            password_confirm="short",
        )


@pytest.mark.unit
def test_registration_form_rejects_bad_email() -> None:
    with pytest.raises(ValidationError):
        RegistrationForm(
            email="not-an-email",
            password="longenough",
            password_confirm="longenough",
        )
