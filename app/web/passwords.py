"""Password hashing for web registration (bcrypt)."""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Return UTF-8 string with bcrypt hash (includes salt)."""
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False
