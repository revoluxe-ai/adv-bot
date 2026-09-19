"""Unit tests for Registry v2 and resolver contracts.

Тесты проверяют machine boundaries, а не внутреннее рассуждение Markdown
command: strict Registry shape, field coverage, explicit/automatic flags,
ordered COMPOSE plan and fixed resolver exit-code mapping.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from tools.scripts import bootstrap, registry, resolver

pytestmark = pytest.mark.unit


def _readiness() -> dict[str, str]:
    """Создать минимальную readiness запись для schema fixture."""
    return {
        "runnable": "UNKNOWN",
        "tests": "NONE",
        "battle_tested": "NO",
        "last_local_at": "-",
        "last_cluster_at": "-",
        "last_image_ref": "-",
        "notes": "",
    }


def _argument() -> dict[str, Any]:
    """Создать non-secret scalar argument для Registry fixture."""
    return {"type": "string", "description": "Fixture value", "secret": False}


def _entry(
    entry_id: str,
    *,
    fields: list[str],
    composable: bool = False,
    compose_with: list[str] | None = None,
    resolution_enabled: bool = True,
    explicit_enabled: bool = True,
) -> dict[str, Any]:
    """Создать validated row fixture для resolution scenarios."""
    result: dict[str, Any] = {
        "id": entry_id,
        "title": entry_id,
        "path": f"scripts/{entry_id}.py",
        "resolution_enabled": resolution_enabled,
        "explicit_invocation_enabled": explicit_enabled,
        "deprecated_by": None,
        "readiness": _readiness(),
    }
    if resolution_enabled:
        result.update(
            {
                "capabilities": ["capability"],
                "sources": ["SOURCE"],
                "provided_fields": fields,
                "required_args": {"value": _argument()},
                "optional_args": {},
                "output_schema_version": "v1",
                "primary_artifact_pattern": "*.zip",
                "tenant_scope": "PARAMETERIZED",
                "hardcoded_context": {"identifiers": [], "justification": ""},
                "composable": composable,
                "compose_with": compose_with or [],
                "side_effects": ["READ_ONLY", "LOCAL_ARTIFACT_WRITE"],
            }
        )
    elif explicit_enabled:
        result.update(
            {
                "provided_fields": fields,
                "required_args": {"value": _argument()},
                "optional_args": {},
                "output_schema_version": "v1",
                "primary_artifact_pattern": "*.zip",
                "tenant_scope": "SPECIAL_PURPOSE",
                "hardcoded_context": {"identifiers": [], "justification": ""},
                "side_effects": ["READ_ONLY", "LOCAL_ARTIFACT_WRITE"],
            }
        )
    return result


def _document(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Создать полный Registry v2 document для validator tests."""
    return json.loads(
        json.dumps(
            {
                "schema": "scripts-registry",
                "version": 2,
                "generated": {"markdown": "scripts/REGISTRY.md", "ordering": "id"},
                "entries": entries,
            },
            sort_keys=True,
        )
    )


def _request(**overrides: Any) -> dict[str, Any]:
    """Создать exact resolver request fixture с zero-write invariant."""
    value: dict[str, Any] = {
        "schema_version": resolver.REQUEST_SCHEMA,
        "mode": "PLAN_RUN",
        "request_id": "req-test",
        "run_id": "run-test",
        "change_name_hint": "test-capability",
        "capabilities": ["capability"],
        "sources": ["SOURCE"],
        "required_fields": ["field-a"],
        "output_schema_version": "v1",
        "primary_artifact_pattern": "*.zip",
        "required_args": {"value": "fixture"},
        "optional_args": {},
        "zero_write_required": True,
        "explicit_script": None,
        "owning_change_id": None,
    }
    value.update(overrides)
    return value


def test_registry_v2_rejects_unknown_top_level_key() -> None:
    """Unknown top-level key fails Registry contract instead of being ignored."""
    document = {
        "schema": "scripts-registry",
        "version": 2,
        "generated": {"markdown": "scripts/REGISTRY.md", "ordering": "id"},
        "entries": [],
        "unexpected": True,
    }
    with pytest.raises(registry.RegistryValidationError):
        registry.validate_document(document)


def test_registry_rejects_unsorted_entries_and_mapping_keys() -> None:
    """Registry rejects non-canonical list and mapping ordering."""
    unsorted_entries = _document([_entry("zeta", fields=["field-a"]), _entry("alpha", fields=["field-a"])])
    with pytest.raises(registry.RegistryValidationError, match="sorted by id"):
        registry.validate_document(unsorted_entries)

    unsorted_mapping = _document([_entry("alpha", fields=["field-a"])])
    unsorted_mapping["entries"][0]["optional_args"] = {
        "z-value": _argument(),
        "a-value": _argument(),
    }
    with pytest.raises(registry.RegistryValidationError, match="mapping keys"):
        registry.validate_document(unsorted_mapping)


def test_registry_accepts_canonical_order_and_renders_same_entry_order() -> None:
    """Canonical Registry order validates and is preserved by Markdown render."""
    document = _document(
        [_entry("alpha", fields=["field-a"]), _entry("zeta", fields=["field-a"])]
    )

    validated = registry.validate_document(document)
    rendered = registry.render_markdown(validated)

    assert [entry["id"] for entry in validated["entries"]] == ["alpha", "zeta"]
    assert rendered.index("alpha") < rendered.index("zeta")


def _canonical_validation_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    markdown_stdout: str,
    markdown_returncode: int = 0,
) -> tuple[resolver.GitIdentity, str]:
    """Подготовить fixed-HEAD ответы для canonical Registry checks."""
    canonical_root = tmp_path / "canonical"
    (canonical_root / "tools" / "scripts").mkdir(parents=True)
    (canonical_root / "tools" / "scripts" / "resolver.py").write_text(
        "# canonical fixture\n", encoding="utf-8"
    )
    document = _document([_entry("alpha", fields=["field-a"])])
    registry_text = yaml.safe_dump(document, sort_keys=True)
    canonical_git = resolver.GitIdentity(
        root=canonical_root,
        branch="refs/heads/scripts",
        sha="1" * 40,
        common_dir=tmp_path / ".git",
    )

    def fake_git(root: Path, *args: str) -> str:
        """Return clean status and fixed Registry containing commit."""
        if args[:1] == ("status",):
            return ""
        if args[:1] == ("log",):
            return "1" * 40
        raise AssertionError(f"unexpected git call: {args}")

    def fake_run(
        command: list[str],
        *,
        capture_output: bool,
        text: bool,
        encoding: str,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        """Serve Registry blobs from the simulated canonical HEAD."""
        blob = str(command[-1])
        if blob.endswith(":scripts/REGISTRY.yaml"):
            return subprocess.CompletedProcess(command, 0, registry_text, "")
        if blob.endswith(":scripts/REGISTRY.md"):
            return subprocess.CompletedProcess(
                command, markdown_returncode, markdown_stdout, ""
            )
        raise AssertionError(f"unexpected subprocess call: {command}")

    monkeypatch.setattr(resolver, "_identity", lambda root: canonical_git)
    monkeypatch.setattr(resolver, "_git", fake_git)
    monkeypatch.setattr(resolver.subprocess, "run", fake_run)
    return canonical_git, registry.render_markdown(document)


def test_validate_canonical_blocks_missing_generated_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Canonical resolution blocks when fixed HEAD lacks REGISTRY.md."""
    canonical_git, _ = _canonical_validation_fixture(tmp_path, monkeypatch, "", 1)

    with pytest.raises(resolver.ResolverBlocked, match="REGISTRY.md"):
        resolver._validate_canonical(
            canonical_git.root,
            _caller_identity(tmp_path),
        )


def test_validate_canonical_blocks_generated_registry_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Canonical resolution blocks when fixed YAML and Markdown drift."""
    canonical_git, expected_markdown = _canonical_validation_fixture(
        tmp_path,
        monkeypatch,
        "# drift\n",
    )
    assert expected_markdown != "# drift\n"

    with pytest.raises(resolver.ResolverBlocked, match="drifted"):
        resolver._validate_canonical(
            canonical_git.root,
            _caller_identity(tmp_path),
        )


def test_validate_canonical_accepts_synchronized_registry_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Canonical resolution accepts a synchronized fixed-HEAD pair."""
    canonical_git, expected_markdown = _canonical_validation_fixture(
        tmp_path,
        monkeypatch,
        "",
    )
    monkeypatch.setattr(
        resolver.subprocess,
        "run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command,
            0,
            yaml.safe_dump(
                _document([_entry("alpha", fields=["field-a"])]),
                sort_keys=True,
            )
            if str(command[-1]).endswith(":scripts/REGISTRY.yaml")
            else expected_markdown,
            "",
        ),
    )

    identity = resolver._validate_canonical(
        canonical_git.root,
        _caller_identity(tmp_path),
    )

    assert identity.registry_sha == "1" * 40


def test_field_coverage_allows_reuse_only_when_required_fields_are_provided() -> None:
    """REUSE requires request.required_fields subset of provided_fields."""
    entry = _entry("one", fields=["field-a", "field-b"])
    assert resolver._compatible(entry, _request()) is True
    assert resolver._compatible(
        entry, _request(required_fields=["field-a", "field-c"])
    ) is False


def test_compose_plan_uses_union_of_child_fields_and_preserves_order() -> None:
    """COMPOSE builds ordered children without semantic data merge."""
    first = _entry("first", fields=["field-a"], composable=True)
    second = _entry("second", fields=["field-b"], composable=True)
    plan = resolver._compose_plan(
        [second, first],
        _request(required_fields=["field-a", "field-b"]),
    )
    assert plan is not None
    assert [child["registry_id"] for child in plan["children"]] == ["first", "second"]
    assert plan["children"][0]["order"] == 1
    assert all("outputs" in child for child in plan["children"])
    assert "merged_payload" not in plan


def test_compose_plan_respects_declared_predecessors() -> None:
    """COMPOSE uses deterministic topological order for declared dependencies."""
    first = _entry("first", fields=["field-a"], composable=True)
    second = _entry("second", fields=["field-b"], composable=True)
    third = _entry(
        "third",
        fields=["field-c"],
        composable=True,
        compose_with=["first"],
    )
    plan = resolver._compose_plan(
        [third, second, first],
        _request(required_fields=["field-a", "field-b", "field-c"]),
    )
    assert plan is not None
    assert [child["registry_id"] for child in plan["children"]] == [
        "first",
        "second",
        "third",
    ]


def test_compose_plan_supports_five_children_without_arbitrary_limit() -> None:
    """Five-child DAGs remain ordered and retain evidence for every child."""
    entries = [
        _entry("first", fields=["field-a"], composable=True),
        _entry(
            "second",
            fields=["field-b"],
            composable=True,
            compose_with=["first"],
        ),
        _entry(
            "third",
            fields=["field-c"],
            composable=True,
            compose_with=["second"],
        ),
        _entry(
            "fourth",
            fields=["field-d"],
            composable=True,
            compose_with=["third"],
        ),
        _entry(
            "fifth",
            fields=["field-e"],
            composable=True,
            compose_with=["fourth"],
        ),
    ]

    plan = resolver._compose_plan(
        list(reversed(entries)),
        _request(required_fields=[f"field-{letter}" for letter in "abcde"]),
    )

    assert plan is not None
    assert [child["registry_id"] for child in plan["children"]] == [
        "first",
        "second",
        "third",
        "fourth",
        "fifth",
    ]
    assert [child["order"] for child in plan["children"]] == [1, 2, 3, 4, 5]
    assert all(child["outputs"] and child["required"] for child in plan["children"])


def test_compose_cycle_is_blocked() -> None:
    """Cyclic composition cannot produce a child Job plan."""
    first = _entry(
        "first",
        fields=["field-a"],
        composable=True,
        compose_with=["second"],
    )
    second = _entry(
        "second",
        fields=["field-b"],
        composable=True,
        compose_with=["first"],
    )
    with pytest.raises(resolver.ResolverBlocked, match="cycle"):
        resolver._compose_plan(
            [first, second],
            _request(required_fields=["field-a", "field-b"]),
        )


def test_registry_rejects_invalid_and_accepts_immutable_image_ref() -> None:
    """Readiness accepts only '-' or an immutable Harbor commit image."""
    valid = _entry("valid", fields=["field-a"])
    valid["readiness"]["last_image_ref"] = (
        "harbor.skyline360.ru/git-registry-cache/revoluxe-ai/adv-bot:"
        "0123456789abcdef0123456789abcdef01234567"
    )
    registry.validate_document(_document([valid]))
    invalid = _entry("invalid", fields=["field-a"])
    invalid["readiness"]["last_image_ref"] = "harbor.example/collector:latest"
    with pytest.raises(registry.RegistryValidationError, match="last_image_ref"):
        registry.validate_document(_document([invalid]))


def test_registry_rejects_composition_graph_errors() -> None:
    """Registry validation rejects unknown and cyclic predecessor graphs."""
    unknown = _entry(
        "unknown",
        fields=["field-a"],
        composable=True,
        compose_with=["missing"],
    )
    with pytest.raises(registry.RegistryValidationError, match="unknown id"):
        registry.validate_document(_document([unknown]))
    first = _entry(
        "first",
        fields=["field-a"],
        composable=True,
        compose_with=["second"],
    )
    second = _entry(
        "second",
        fields=["field-b"],
        composable=True,
        compose_with=["first"],
    )
    with pytest.raises(registry.RegistryValidationError, match="cycle"):
        registry.validate_document(_document([first, second]))


def test_disabled_explicit_row_is_not_automatic_but_can_be_explicit() -> None:
    """resolution_enabled и explicit_invocation_enabled остаются раздельными."""
    entry = _entry(
        "cabinet401",
        fields=["field-a"],
        resolution_enabled=False,
        explicit_enabled=True,
    )
    request = _request(explicit_script="cabinet401")
    assert resolver._compatible(entry, request) is False
    assert resolver._compatible_explicit(entry, request) is True


def test_malformed_request_has_machine_invalid_request_contract() -> None:
    """Missing required request fields is classified as INVALID_REQUEST."""
    with pytest.raises(resolver.InvalidRequest):
        resolver.validate_request({"mode": "PLAN_RUN"}, "PLAN_RUN")


def test_credential_request_is_rejected_without_echoing_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Credential-like request material never reaches machine output."""
    secret = "Bearer UNIQUE-RESOLVER-SECRET-SENTINEL"
    request_file = tmp_path / "request.json"
    request_file.write_text(
        json.dumps(_request(required_args={"api_key": secret})),
        encoding="utf-8",
    )
    assert (
        resolver.main(
            [
                "PLAN_RUN",
                "--request-file",
                str(request_file.resolve()),
                "--caller-root",
                str(tmp_path.resolve()),
            ]
        )
        == 2
    )
    captured = capsys.readouterr()
    assert secret not in captured.out
    assert secret not in captured.err


def test_formal_handoff_is_sanitized_and_does_not_issue_apply() -> None:
    """Formal handoff contains a prohibition, not an automatic apply command."""
    request = _request()
    caller = resolver.GitIdentity(
        root=Path("C:/caller"),
        branch="refs/heads/feature",
        sha="0" * 40,
        common_dir=Path("C:/repo/.git"),
    )
    canonical_git = resolver.GitIdentity(
        root=Path("C:/scripts"),
        branch="refs/heads/scripts",
        sha="1" * 40,
        common_dir=Path("C:/repo/.git"),
    )
    canonical = resolver.CanonicalIdentity(
        git=canonical_git,
        registry_text="",
        registry_sha="1" * 40,
    )
    handoff = resolver._formal_change(request, caller, canonical)
    serialized = json.dumps(handoff, ensure_ascii=False)
    assert "/opsx-apply" not in handoff["pasteable_prompt"]
    assert "apply=PROHIBITED" in handoff["pasteable_prompt"]
    assert serialized.count("FORMAL_CHANGE_REQUIRED") >= 1


def test_ambiguous_automatic_resolution_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multiple fully compatible rows cannot silently choose one collector."""
    first = _entry("first", fields=["field-a"])
    second = _entry("second", fields=["field-a"])
    caller = resolver.GitIdentity(
        root=tmp_path,
        branch="refs/heads/feature",
        sha="0" * 40,
        common_dir=tmp_path / ".git",
    )
    canonical = resolver.CanonicalIdentity(
        git=resolver.GitIdentity(
            root=tmp_path,
            branch="refs/heads/scripts",
            sha="1" * 40,
            common_dir=tmp_path / ".git",
        ),
        registry_text=yaml.safe_dump(_document([first, second])),
        registry_sha="1" * 40,
    )
    monkeypatch.setattr(resolver, "_identity", lambda root: caller)
    monkeypatch.setattr(
        resolver,
        "discover_canonical",
        lambda ignored_caller, ignored_root: canonical,
    )
    result = resolver.resolve("PLAN_RUN", _request(), tmp_path)
    assert result["outcome"] == "BLOCKED"
    assert result["error"]["code"] == "AMBIGUOUS_AUTOMATIC_RESOLUTION"
    assert result["error"]["candidates"] == ["first", "second"]


def test_malformed_json_cli_emits_blocked_result_without_write_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Malformed JSON exits 2 and emits one machine-readable BLOCKED result."""
    request_file = tmp_path / "request.json"
    request_file.write_text("{not-json", encoding="utf-8")
    exit_code = resolver.main(
        [
            "PLAN_RUN",
            "--request-file",
            str(request_file.resolve()),
            "--caller-root",
            str(tmp_path.resolve()),
        ]
    )
    result = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert result["outcome"] == "BLOCKED"
    assert result["error"]["code"] == "INVALID_REQUEST"
    assert result["request_id"] is None
    assert result["run_id"] is None
    assert result["operational_write_path"] is False


def test_resolver_exit_code_contract_is_fixed() -> None:
    """All four operational outcomes map to their normative exit codes."""
    assert resolver._exit_code("REUSE") == 0
    assert resolver._exit_code("COMPOSE") == 0
    assert resolver._exit_code("FORMAL_CHANGE_REQUIRED") == 10
    assert resolver._exit_code("BLOCKED") == 20
    assert resolver._exit_code("BLOCKED", malformed=True) == 2
    assert resolver._exit_code("BLOCKED", unexpected=True) == 30


def test_hardcoding_gate_skips_disabled_rows_and_blocks_enabled_rows() -> None:
    """Hardcoding gate protects automatic rows without backfilling legacy rows."""
    enabled = _entry("enabled", fields=["field-a"])
    source = 'SHOP_ID = "fixed"\n'
    assert registry.hardcoding_errors(enabled, source)
    disabled = _entry(
        "legacy",
        fields=["field-a"],
        resolution_enabled=False,
        explicit_enabled=False,
    )
    assert registry.hardcoding_errors(disabled, source) == []


def _caller_identity(tmp_path: Path) -> resolver.GitIdentity:
    """Создать caller identity для canonical-root precedence tests."""
    return resolver.GitIdentity(
        root=tmp_path,
        branch="refs/heads/feature",
        sha="a" * 40,
        common_dir=tmp_path / ".git",
    )


def test_cli_canonical_root_precedes_environment_and_topology(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI override is selected before environment and topology."""
    caller = _caller_identity(tmp_path)
    cli_root = tmp_path / "cli"
    env_root = tmp_path / "env"
    calls: list[Path] = []
    monkeypatch.setenv("SCRIPTS_CANONICAL_ROOT", str(env_root))
    monkeypatch.setattr(
        resolver,
        "_validate_canonical",
        lambda candidate, ignored: calls.append(candidate) or object(),
    )
    monkeypatch.setattr(
        resolver,
        "_git",
        lambda *args: pytest.fail("topology must not be read"),
    )

    result = resolver.discover_canonical(caller, str(cli_root))

    assert result is not None
    assert calls == [cli_root.resolve()]


def test_environment_canonical_root_precedes_topology(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Environment override is selected before topology discovery."""
    caller = _caller_identity(tmp_path)
    env_root = tmp_path / "env"
    calls: list[Path] = []
    monkeypatch.setenv("SCRIPTS_CANONICAL_ROOT", str(env_root))
    monkeypatch.setattr(
        resolver,
        "_validate_canonical",
        lambda candidate, ignored: calls.append(candidate) or object(),
    )
    monkeypatch.setattr(
        resolver,
        "_git",
        lambda *args: pytest.fail("topology must not be read"),
    )

    result = resolver.discover_canonical(caller, None)

    assert result is not None
    assert calls == [env_root.resolve()]


@pytest.mark.parametrize("source", ["cli", "environment"])
def test_invalid_explicit_canonical_root_does_not_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """Invalid explicit roots block without trying lower-precedence sources."""
    caller = _caller_identity(tmp_path)
    invalid_root = tmp_path / source
    topology_root = tmp_path / "topology"
    calls: list[Path] = []

    def reject(candidate: Path, ignored: resolver.GitIdentity) -> object:
        """Reject the selected explicit root without allowing fallback."""
        calls.append(candidate)
        raise resolver.ResolverBlocked("invalid explicit root")

    monkeypatch.setattr(
        resolver,
        "_validate_canonical",
        reject,
    )
    monkeypatch.setattr(
        resolver,
        "_git",
        lambda *args: pytest.fail("lower-precedence topology must not be used"),
    )
    if source == "environment":
        monkeypatch.setenv("SCRIPTS_CANONICAL_ROOT", str(invalid_root))
        explicit = None
    else:
        monkeypatch.setenv("SCRIPTS_CANONICAL_ROOT", str(topology_root))
        explicit = str(invalid_root)

    with pytest.raises(resolver.ResolverBlocked, match="invalid explicit root"):
        resolver.discover_canonical(caller, explicit)

    assert calls == [invalid_root.resolve()]


def test_missing_canonical_candidates_returns_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Topology without an exact valid scripts candidate is blocked."""
    caller = _caller_identity(tmp_path)
    monkeypatch.delenv("SCRIPTS_CANONICAL_ROOT", raising=False)
    monkeypatch.setattr(resolver, "_git", lambda *args: "")
    monkeypatch.setattr(resolver, "_parse_worktrees", lambda output: [])

    with pytest.raises(resolver.ResolverBlocked, match="no valid"):
        resolver.discover_canonical(caller, None)


def test_multiple_valid_topology_candidates_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Два валидных canonical worktree не могут выбраться по порядку."""
    caller = _caller_identity(tmp_path)
    first = resolver.CanonicalIdentity(
        git=resolver.GitIdentity(
            root=tmp_path / "first",
            branch="refs/heads/scripts",
            sha="1" * 40,
            common_dir=caller.common_dir,
        ),
        registry_text="",
        registry_sha="1" * 40,
    )
    second = resolver.CanonicalIdentity(
        git=resolver.GitIdentity(
            root=tmp_path / "second",
            branch="refs/heads/scripts",
            sha="2" * 40,
            common_dir=caller.common_dir,
        ),
        registry_text="",
        registry_sha="2" * 40,
    )
    monkeypatch.delenv("SCRIPTS_CANONICAL_ROOT", raising=False)
    monkeypatch.setattr(resolver, "_git", lambda *args: "topology")
    monkeypatch.setattr(
        resolver,
        "_parse_worktrees",
        lambda output: [(first.git.root, first.git.branch), (second.git.root, second.git.branch)],
    )
    monkeypatch.setattr(
        resolver,
        "_validate_canonical",
        lambda candidate, ignored: first if candidate == first.git.root else second,
    )

    with pytest.raises(resolver.ResolverBlocked, match="ambiguous canonical topology"):
        resolver.discover_canonical(caller, None)


def test_topology_uses_only_one_valid_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Один валидный кандидат выбирается среди невалидных."""
    caller = _caller_identity(tmp_path)
    valid_root = tmp_path / "valid"
    invalid_root = tmp_path / "invalid"
    expected = resolver.CanonicalIdentity(
        git=resolver.GitIdentity(
            root=valid_root,
            branch="refs/heads/scripts",
            sha="1" * 40,
            common_dir=caller.common_dir,
        ),
        registry_text="",
        registry_sha="1" * 40,
    )

    def validate(candidate: Path, ignored: resolver.GitIdentity) -> resolver.CanonicalIdentity:
        """Сымитировать один валидный и один отклонённый topology candidate."""
        if candidate == invalid_root:
            raise resolver.ResolverBlocked("invalid candidate")
        return expected

    monkeypatch.delenv("SCRIPTS_CANONICAL_ROOT", raising=False)
    monkeypatch.setattr(resolver, "_git", lambda *args: "topology")
    monkeypatch.setattr(
        resolver,
        "_parse_worktrees",
        lambda output: [
            (invalid_root, "refs/heads/scripts"),
            (valid_root, "refs/heads/scripts"),
        ],
    )
    monkeypatch.setattr(resolver, "_validate_canonical", validate)

    assert resolver.discover_canonical(caller, None) is expected


def test_bootstrap_public_selection_fails_closed_on_ambiguity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Публичный bootstrap selector блокирует два валидных topology candidates."""
    caller = _caller_identity(tmp_path)
    roots = [tmp_path / "first", tmp_path / "second"]
    for root in roots:
        (root / "tools/scripts").mkdir(parents=True)
        (root / "tools/scripts/resolver.py").write_text("# fixture\n", encoding="utf-8")

    def identity(root: Path) -> resolver.GitIdentity:
        """Вернуть одинаковую common-dir identity для bootstrap fixture."""
        return resolver.GitIdentity(
            root=root,
            branch="refs/heads/scripts",
            sha="1" * 40,
            common_dir=caller.common_dir,
        )

    monkeypatch.setattr(bootstrap, "_identity", identity)
    monkeypatch.setattr(bootstrap, "_git", lambda *args: "")
    monkeypatch.setattr(
        bootstrap,
        "_parse_worktrees",
        lambda output: [(roots[0], "refs/heads/scripts"), (roots[1], "refs/heads/scripts")],
    )

    with pytest.raises(resolver.ResolverBlocked, match="ambiguous canonical topology"):
        bootstrap.select_canonical_root(caller.root, None)
