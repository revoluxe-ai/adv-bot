"""Unit tests for web password helpers."""

from __future__ import annotations

import pytest

from app.web.passwords import hash_password, verify_password


@pytest.mark.unit
def test_hash_and_verify_roundtrip() -> None:
    h = hash_password("my-secret-password")
    assert h != "my-secret-password"
    assert verify_password("my-secret-password", h)
    assert not verify_password("wrong", h)


@pytest.mark.unit
def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password("x", "not-a-bcrypt-string")
