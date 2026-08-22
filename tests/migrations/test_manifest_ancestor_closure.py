"""Unit: ancestor_closure учитывает depends_on даже при down_revision=None."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.db.manifest import ancestor_closure


def test_ancestor_closure_follows_depends_on_when_down_is_none() -> None:
    revs = {
        "head": SimpleNamespace(
            revision="head",
            down_revision=None,
            depends_on="side",
            path="alembic_/versions/head.py",
        ),
        "side": SimpleNamespace(
            revision="side",
            down_revision=None,
            depends_on=None,
            path="alembic_/versions/side.py",
        ),
    }

    class FakeScript:
        def get_revision(self, rid: str) -> SimpleNamespace:
            return revs[rid]

    with patch("app.db.manifest.ScriptDirectory") as sd:
        sd.from_config.return_value = FakeScript()
        closure = ancestor_closure(["head"])
    assert closure == {"head", "side"}
