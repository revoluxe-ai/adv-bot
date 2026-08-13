"""Доказательство interaction-free класса разрешений Python-конфликтов.

R11 разрешает автономный union только для append-only функций, которые не
читают module globals, не вызывают функции и не имеют внешних эффектов.
Source-level encoding/lint/type/coverage directives обязаны совпадать с base.
"""

from __future__ import annotations

import ast
import io
import re
import tokenize
from dataclasses import dataclass
from typing import Mapping

from .errors import StopRequired
from .hashutil import sha256_text

_ENCODING_RE = re.compile(r"coding[:=]\s*([-\w.]+)")
_BEHAVIOR_DIRECTIVE_RE = re.compile(
    r"#\s*(?:noqa\b|pyright\s*:|type\s*:\s*ignore\b|"
    r"pragma\s*:\s*no\s*cover\b|coverage\s*:|mypy\s*:|"
    r"ruff\s*:|fmt\s*:|isort\s*:|pylint\s*:|flake8\s*:)",
    re.IGNORECASE,
)
_PURE_EXPRESSION_NODES = (
    ast.Constant,
    ast.Name,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Tuple,
    ast.List,
    ast.Set,
    ast.Dict,
    ast.Load,
    ast.operator,
    ast.unaryop,
    ast.boolop,
    ast.cmpop,
)
_MODULE_NAMESPACE_HOOKS = frozenset({"__all__", "__dir__", "__getattr__"})
_RESERVED_MODULE_BINDINGS = frozenset(
    {
        "__all__",
        "__annotations__",
        "__builtins__",
        "__cached__",
        "__dir__",
        "__file__",
        "__getattr__",
        "__loader__",
        "__name__",
        "__package__",
        "__path__",
        "__spec__",
    }
)


@dataclass(frozen=True)
class ResolutionProofResult:
    """Outcome of semantic proof for one path."""

    path: str
    strategy: str
    stage2_sha256: str
    stage3_sha256: str
    resolution_sha256: str
    preserved_from_stage2: tuple[str, ...]
    preserved_from_stage3: tuple[str, ...]


def _parse_module(text: str, *, path: str, side: str) -> ast.Module:
    """Разобрать Python без допуска undecodable/binary содержимого."""
    if "\x00" in text:
        raise StopRequired("STRUCTURAL_PROOF_BINARY_CONTENT", {"path": path, "side": side})
    try:
        return ast.parse(text, filename=f"{path}:{side}", type_comments=True)
    except (SyntaxError, ValueError) as exc:
        raise StopRequired(
            "STRUCTURAL_PROOF_PARSE_FAILED",
            {"path": path, "side": side, "error": str(exc)},
        ) from exc


def _node_dump(node: ast.AST) -> str:
    """Вернуть location-independent AST identity."""
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _body_dumps(module: ast.Module) -> tuple[str, ...]:
    return tuple(_node_dump(node) for node in module.body)


def _type_ignore_dumps(module: ast.Module) -> tuple[str, ...]:
    return tuple(_node_dump(node) for node in module.type_ignores)


def _source_directives(text: str, *, path: str, side: str) -> tuple[tuple[int, str], ...]:
    """Вернуть source directives, невидимые в обычном AST."""
    lines = text.splitlines()
    encodings: list[str] = []
    for line in lines[:2]:
        match = _ENCODING_RE.search(line)
        if match:
            encodings.append(match.group(1).lower().replace("_", "-"))
    if any(value not in {"utf-8", "utf8"} for value in encodings):
        raise StopRequired(
            "STRUCTURAL_PROOF_UNSUPPORTED_ENCODING_DIRECTIVE",
            {"path": path, "side": side, "encodings": encodings},
        )
    return tuple(
        (line_number, line)
        for line_number, line in enumerate(lines, start=1)
        if _ENCODING_RE.search(line)
        or _BEHAVIOR_DIRECTIVE_RE.search(line)
        or (line_number == 1 and line.startswith("#!"))
    )


def _source_comments(
    text: str,
    *,
    path: str,
    side: str,
) -> tuple[tuple[int, int, str], ...]:
    """Return every comment token; autonomous union may not change comments."""
    try:
        tokens = tokenize.generate_tokens(io.StringIO(text).readline)
        return tuple(
            (token.start[0], token.start[1], token.string)
            for token in tokens
            if token.type == tokenize.COMMENT
        )
    except (IndentationError, tokenize.TokenError) as exc:
        raise StopRequired(
            "STRUCTURAL_PROOF_TOKENIZE_FAILED",
            {"path": path, "side": side, "error": str(exc)},
        ) from exc


def _assert_no_reserved_module_bindings(
    module: ast.Module,
    *,
    path: str,
    side: str,
) -> None:
    """Reject implicit/reserved module bindings and namespace hooks."""
    reserved = sorted(_module_bound_names(module) & _RESERVED_MODULE_BINDINGS)
    if reserved:
        raise StopRequired(
            "STRUCTURAL_PROOF_RESERVED_MODULE_BINDING",
            {"path": path, "side": side, "names": reserved},
        )


def _assert_no_module_namespace_hooks(
    module: ast.Module,
    *,
    path: str,
    side: str,
) -> None:
    """Reject module hooks and enforce the closed autonomous AST grammar."""
    _assert_no_reserved_module_bindings(module, path=path, side=side)
    _assert_closed_autonomous_grammar(module, path=path, side=side)
    hooks = sorted(_module_bound_names(module) & _MODULE_NAMESPACE_HOOKS)
    if hooks:
        raise StopRequired(
            "STRUCTURAL_PROOF_MODULE_NAMESPACE_HOOK",
            {"path": path, "side": side, "names": hooks},
        )


# Closed allowlist for autonomous AST-union modules. Anything outside this
# grammar (Call, Attribute, Subscript, Import, ClassDef, …) is STOP — not a
# denylist of known reflection names.
_ALLOWED_AUTONOMOUS_NODES: frozenset[type] = frozenset(
    {
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.arguments,
        ast.arg,
        ast.Return,
        ast.Assign,
        ast.Pass,
        ast.Expr,
        ast.Constant,
        ast.Name,
        ast.Load,
        ast.Store,
        ast.BinOp,
        ast.UnaryOp,
        ast.BoolOp,
        ast.Compare,
        ast.IfExp,
        ast.Tuple,
        ast.List,
        ast.Set,
        ast.Dict,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.LShift,
        ast.RShift,
        ast.BitOr,
        ast.BitXor,
        ast.BitAnd,
        ast.MatMult,
        ast.And,
        ast.Or,
        ast.Not,
        ast.Invert,
        ast.UAdd,
        ast.USub,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Is,
        ast.IsNot,
        ast.In,
        ast.NotIn,
    }
)


def _assert_closed_autonomous_grammar(
    module: ast.Module,
    *,
    path: str,
    side: str,
) -> None:
    """Prove the module is inside the autonomous closed AST allowlist.

    Base and side modules may only contain interaction-free function
    definitions: no calls, attributes, subscripts, imports, or classes.
    This replaces denylist reflection chasing.
    """
    for node in module.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            # Module docstring only.
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        raise StopRequired(
            "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
            {
                "path": path,
                "side": side,
                "node": type(node).__name__,
                "where": "module_body",
            },
        )
    for node in ast.walk(module):
        if type(node) not in _ALLOWED_AUTONOMOUS_NODES:
            raise StopRequired(
                "STRUCTURAL_PROOF_ALLOWLIST_VIOLATION",
                {
                    "path": path,
                    "side": side,
                    "node": type(node).__name__,
                    "where": "ast_walk",
                },
            )
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _assert_interaction_free_function(node, path=path, side=side)
            # Reuse import-time risk checks from addition path.
            _simple_function_name(node, path=path, side=side)


def _module_bound_names(module: ast.Module) -> set[str]:
    """Conservatively collect every name which base may bind."""
    names: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add(alias.asname or alias.name.split(".", 1)[0])
    return names


def _assert_pure_expression(
    node: ast.AST,
    *,
    allowed_names: set[str],
    path: str,
    side: str,
    function: str,
) -> None:
    """Reject expressions which may access globals or trigger user code."""
    for child in ast.walk(node):
        if not isinstance(child, _PURE_EXPRESSION_NODES):
            raise StopRequired(
                "STRUCTURAL_PROOF_EXTERNAL_EFFECT_OR_DYNAMIC_ACCESS",
                {
                    "path": path,
                    "side": side,
                    "function": function,
                    "node": type(child).__name__,
                },
            )
        if (
            isinstance(child, ast.Name)
            and isinstance(child.ctx, ast.Load)
            and child.id not in allowed_names
        ):
            raise StopRequired(
                "STRUCTURAL_PROOF_GLOBAL_READ",
                {
                    "path": path,
                    "side": side,
                    "function": function,
                    "name": child.id,
                },
            )


def _assert_interaction_free_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    path: str,
    side: str,
) -> None:
    """Prove that a function is closed over arguments/constants and effect-free."""
    allowed_names = {
        arg.arg
        for arg in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        )
    }
    if node.args.vararg:
        allowed_names.add(node.args.vararg.arg)
    if node.args.kwarg:
        allowed_names.add(node.args.kwarg.arg)

    for statement in node.body:
        if isinstance(statement, ast.Return):
            if statement.value is not None:
                _assert_pure_expression(
                    statement.value,
                    allowed_names=allowed_names,
                    path=path,
                    side=side,
                    function=node.name,
                )
            continue
        if isinstance(statement, ast.Assign) and all(
            isinstance(target, ast.Name) for target in statement.targets
        ):
            _assert_pure_expression(
                statement.value,
                allowed_names=allowed_names,
                path=path,
                side=side,
                function=node.name,
            )
            allowed_names.update(
                target.id for target in statement.targets if isinstance(target, ast.Name)
            )
            continue
        raise StopRequired(
            "STRUCTURAL_PROOF_EFFECTFUL_FUNCTION_BODY",
            {
                "path": path,
                "side": side,
                "function": node.name,
                "node": type(statement).__name__,
            },
        )


def _simple_function_name(node: ast.stmt, *, path: str, side: str) -> str:
    """Принять только interaction-free definition без import-time execution."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise StopRequired(
            "STRUCTURAL_PROOF_NON_FUNCTION_ADDITION",
            {"path": path, "side": side, "node": type(node).__name__},
        )
    if node.name in _MODULE_NAMESPACE_HOOKS:
        raise StopRequired(
            "STRUCTURAL_PROOF_MODULE_NAMESPACE_HOOK",
            {"path": path, "side": side, "names": [node.name]},
        )
    args = node.args
    annotated = [
        arg.arg
        for arg in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        if arg.annotation is not None
    ]
    if args.vararg and args.vararg.annotation is not None:
        annotated.append(args.vararg.arg)
    if args.kwarg and args.kwarg.annotation is not None:
        annotated.append(args.kwarg.arg)
    if (
        node.decorator_list
        or node.returns is not None
        or args.defaults
        or any(default is not None for default in args.kw_defaults)
        or annotated
        or node.type_comment is not None
    ):
        raise StopRequired(
            "STRUCTURAL_PROOF_IMPORT_TIME_EXECUTION_RISK",
            {"path": path, "side": side, "function": node.name},
        )
    _assert_interaction_free_function(node, path=path, side=side)
    return node.name


def _added_functions(
    *,
    base: ast.Module,
    side: ast.Module,
    path: str,
    side_name: str,
    base_text: str,
    side_text: str,
) -> tuple[ast.stmt, ...]:
    """Проверить, что side равен base AST плюс append-only functions."""
    base_body = _body_dumps(base)
    side_body = _body_dumps(side)
    if side_body[: len(base_body)] != base_body:
        raise StopRequired(
            "STRUCTURAL_PROOF_BASE_MODIFIED",
            {"path": path, "side": side_name},
        )
    additions = tuple(side.body[len(base.body) :])
    if not additions:
        raise StopRequired(
            "STRUCTURAL_PROOF_SIDE_HAS_NO_ADDITION",
            {"path": path, "side": side_name},
        )
    for node in additions:
        _simple_function_name(node, path=path, side=side_name)
    if _type_ignore_dumps(side) != _type_ignore_dumps(base):
        raise StopRequired(
            "STRUCTURAL_PROOF_TYPE_IGNORE_CHANGED",
            {"path": path, "side": side_name},
        )
    if _source_directives(side_text, path=path, side=side_name) != _source_directives(
        base_text,
        path=path,
        side="base",
    ):
        raise StopRequired(
            "STRUCTURAL_PROOF_SOURCE_DIRECTIVE_CHANGED",
            {"path": path, "side": side_name},
        )
    if _source_comments(side_text, path=path, side=side_name) != _source_comments(
        base_text,
        path=path,
        side="base",
    ):
        raise StopRequired(
            "STRUCTURAL_PROOF_SOURCE_COMMENT_CHANGED",
            {"path": path, "side": side_name},
        )
    return additions


def prove_text_resolution(
    *,
    path: str,
    resolution: str,
    stage_blobs: Mapping[int, str],
    topology: str,
) -> ResolutionProofResult:
    """
    Доказать точный AST-union append-only функций обеих сторон.

    Args:
        path: repo-relative path
        resolution: proposed file text
        stage_blobs: stage number → blob text (1=base, 2=ours/current, 3=theirs)
        topology: conflict taxonomy label

    Returns:
        ResolutionProofResult on success

    Raises:
        StopRequired: when semantics cannot be proven
    """
    if topology != "modify/modify":
        raise StopRequired(
            "SEMANTIC_PROOF_UNSUPPORTED_TOPOLOGY",
            {"path": path, "topology": topology},
        )
    if 2 not in stage_blobs or 3 not in stage_blobs:
        raise StopRequired("SEMANTIC_PROOF_MISSING_STAGE_BLOBS", {"path": path})

    if not path.endswith(".py"):
        raise StopRequired(
            "STRUCTURAL_PROOF_UNSUPPORTED_FILE_TYPE",
            {"path": path, "supported": [".py"]},
        )
    if 1 not in stage_blobs:
        raise StopRequired("STRUCTURAL_PROOF_MISSING_BASE", {"path": path})

    s1 = stage_blobs[1]
    s2 = stage_blobs[2]
    s3 = stage_blobs[3]
    if not resolution or not resolution.strip():
        raise StopRequired("SEMANTIC_RESOLUTION_EMPTY", {"path": path})

    base = _parse_module(s1, path=path, side="base")
    stage2 = _parse_module(s2, path=path, side="stage2")
    stage3 = _parse_module(s3, path=path, side="stage3")
    candidate = _parse_module(resolution, path=path, side="resolution")
    for module, side in (
        (base, "base"),
        (stage2, "stage2"),
        (stage3, "stage3"),
        (candidate, "resolution"),
    ):
        _assert_no_module_namespace_hooks(module, path=path, side=side)
    add2 = _added_functions(
        base=base,
        side=stage2,
        path=path,
        side_name="stage2",
        base_text=s1,
        side_text=s2,
    )
    add3 = _added_functions(
        base=base,
        side=stage3,
        path=path,
        side_name="stage3",
        base_text=s1,
        side_text=s3,
    )

    names2 = tuple(_simple_function_name(node, path=path, side="stage2") for node in add2)
    names3 = tuple(_simple_function_name(node, path=path, side="stage3") for node in add3)
    if set(names2) & set(names3):
        raise StopRequired(
            "STRUCTURAL_PROOF_DUPLICATE_ADDED_SYMBOL",
            {"path": path, "names": sorted(set(names2) & set(names3))},
        )
    base_names = _module_bound_names(base)
    if base_names & (set(names2) | set(names3)):
        raise StopRequired(
            "STRUCTURAL_PROOF_REDEFINES_BASE_SYMBOL",
            {"path": path, "names": sorted(base_names & (set(names2) | set(names3)))},
        )

    base_dump = _body_dumps(base)
    candidate_dump = _body_dumps(candidate)
    expected_23 = base_dump + tuple(_node_dump(node) for node in (*add2, *add3))
    expected_32 = base_dump + tuple(_node_dump(node) for node in (*add3, *add2))
    if candidate_dump not in {expected_23, expected_32}:
        raise StopRequired(
            "STRUCTURAL_PROOF_EXACT_UNION_MISMATCH",
            {
                "path": path,
                "stage2_additions": names2,
                "stage3_additions": names3,
            },
        )
    if _type_ignore_dumps(candidate) != _type_ignore_dumps(base):
        raise StopRequired("STRUCTURAL_PROOF_TYPE_IGNORE_CHANGED", {"path": path})
    if _source_directives(
        resolution,
        path=path,
        side="resolution",
    ) != _source_directives(s1, path=path, side="base"):
        raise StopRequired("STRUCTURAL_PROOF_SOURCE_DIRECTIVE_CHANGED", {"path": path})
    if _source_comments(
        resolution,
        path=path,
        side="resolution",
    ) != _source_comments(s1, path=path, side="base"):
        raise StopRequired("STRUCTURAL_PROOF_SOURCE_COMMENT_CHANGED", {"path": path})

    return ResolutionProofResult(
        path=path,
        strategy="namespace_closed_comment_exact_ast_union",
        stage2_sha256=sha256_text(s2),
        stage3_sha256=sha256_text(s3),
        resolution_sha256=sha256_text(resolution),
        preserved_from_stage2=names2,
        preserved_from_stage3=names3,
    )
