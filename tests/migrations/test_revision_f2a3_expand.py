"""Unit: статический контракт Expand-ревизии f2a3b4c5d6e7."""

from pathlib import Path


def test_f2a3_adds_emergency_latch_columns() -> None:
    """Ревизия добавляет latch/educated без app imports."""
    path = Path("alembic_/versions/f2a3b4c5d6e7_add_card_ab_hold_emergency_latch.py")
    text = path.read_text(encoding="utf-8")
    assert 'revision: str = "f2a3b4c5d6e7"' in text
    assert 'down_revision: Union[str, None] = "d0e1f2a3b4c5"' in text
    assert "card_ab_hold_emergency_latch" in text
    assert "card_ab_hold_emergency_educated" in text
    assert "from app." not in text
    assert "server_default=sa.text(\"false\")" in text
