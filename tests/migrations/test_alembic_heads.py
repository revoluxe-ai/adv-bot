"""Unit: в script directory ровно один Alembic head."""

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_exactly_one_alembic_head() -> None:
    """Репозиторий должен иметь единственный ожидаемый head."""

    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    assert len(heads) == 1, heads
    assert heads[0] == "0b0fe484ba6b"
