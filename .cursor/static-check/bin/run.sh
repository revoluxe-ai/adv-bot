#!/usr/bin/env bash
# Repo-root runner for /opsx-static-check workers.
# Works under Git Bash (MSYS) and WSL when the venv is a Windows .venv.
# Usage: bash .cursor/static-check/bin/run.sh -- <command...>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

VENV_SCRIPTS="${REPO_ROOT}/.venv/Scripts"
VENV_BIN="${REPO_ROOT}/.venv/bin"

# Do NOT source ~/.bashrc here: it can prepend npm shims (broken pyright/node).

resolve_tool() {
  # Prefer explicit venv binaries (with .exe on Windows venvs).
  local name="$1"
  local candidate
  for candidate in \
    "${VENV_SCRIPTS}/${name}.exe" \
    "${VENV_SCRIPTS}/${name}" \
    "${VENV_BIN}/${name}"
  do
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

die_missing() {
  echo "run.sh: missing venv tool '$1' under ${VENV_SCRIPTS} or ${VENV_BIN}" >&2
  exit 127
}

if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ "$#" -lt 1 ]]; then
  echo "usage: run.sh -- <command...>" >&2
  exit 2
fi

CMD=("$1")
shift

case "${CMD[0]}" in
  pyright-strict)
    PYRIGHT_BIN="$(resolve_tool pyright)" || die_missing pyright
    exec "${PYRIGHT_BIN}" --project pyrightconfig_strict.json "$@"
    ;;
  mypy)
    MYPY_BIN="$(resolve_tool mypy)" || die_missing mypy
    exec "${MYPY_BIN}" "$@"
    ;;
  poetry)
    POETRY_BIN="$(resolve_tool poetry)" || die_missing poetry
    exec "${POETRY_BIN}" "$@"
    ;;
  *)
    # Unknown first token: still force venv Scripts ahead of PATH, then exec.
    export PATH="${VENV_SCRIPTS}:${VENV_BIN}:${PATH:-}"
    exec "${CMD[0]}" "$@"
    ;;
esac
