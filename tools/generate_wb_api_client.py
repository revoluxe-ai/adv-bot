"""Generate a WB API client package from the Wildberries OpenAPI specification."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, urlopen


def fetch_spec_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "wb-api-client-generator/1.0"})
    with urlopen(request) as response:
        return response.read()


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_spec_lock(
    *,
    spec_key: str,
    spec_url: str,
    spec_filename: str,
    spec_bytes: bytes,
    generator: str,
    generator_meta: str,
) -> dict[str, str | int]:
    return {
        "spec_key": spec_key,
        "spec_url": spec_url,
        "spec_filename": spec_filename,
        "sha256": compute_sha256(spec_bytes),
        "size_bytes": len(spec_bytes),
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "generator": generator,
        "generator_meta": generator_meta,
    }


def write_spec_lock(lock_path: Path, lock_data: dict[str, str | int]) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps(lock_data, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_spec_lock(lock_path: Path) -> dict[str, str | int]:
    return json.loads(lock_path.read_text(encoding="utf-8"))


def lock_path_for(swagger_dir: Path) -> Path:
    return swagger_dir / "spec.lock.json"


def copy_generated_contents(src: Path, dest: Path) -> None:
    for entry in src.iterdir():
        target = dest / entry.name
        if entry.is_dir():
            shutil.copytree(entry, target, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, target)


def run_generator(spec_path: Path, output_path: Path, meta: str, python_cmd: str) -> None:
    cmd = [
        python_cmd,
        "generate",
        "--path",
        str(spec_path),
        "--meta",
        meta,
    ]
    print(f"Running OpenAPI client generator: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True, cwd=output_path)


def run_transliteration(script_path: Path, input_path: Path, output_path: Path) -> None:
    cmd = [sys.executable, str(script_path), str(input_path), str(output_path)]
    print(f"Running transliteration: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class SwaggerTarget:
    key: str
    spec_url: str
    spec_filename: str
    target_root: Path
    package_name: str
    skip_transliteration: bool = False


SWAGGER_TARGETS: dict[str, SwaggerTarget] = {
    "promotion": SwaggerTarget(
        key="promotion",
        spec_url="https://dev.wildberries.ru/api/swagger/yaml/en/08-promotion.yaml",
        spec_filename="08-promotion.yaml",
        target_root=REPO_ROOT / "app" / "core" / "mp" / "wb" / "api" / "generated" / "promotion",
        package_name="marketing_and_promotions_client",
        skip_transliteration=True,
    ),
    "products": SwaggerTarget(
        key="products",
        spec_url="https://dev.wildberries.ru/api/swagger/yaml/ru/02-products.yaml",
        spec_filename="02-products.yaml",
        target_root=REPO_ROOT / "app" / "core" / "mp" / "wb" / "api" / "generated" / "products",
        package_name="content_products_client",
    ),
    "reports": SwaggerTarget(
        key="reports",
        spec_url="https://dev.wildberries.ru/api/swagger/yaml/en/12-reports.yaml",
        spec_filename="12-reports.yaml",
        target_root=REPO_ROOT / "app" / "core" / "mp" / "wb" / "api" / "generated" / "reports",
        package_name="reports_client",
        skip_transliteration=True,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Wildberries OpenAPI specs and generate versioned clients."
    )
    parser.add_argument(
        "--spec-key",
        choices=list(SWAGGER_TARGETS),
        default="promotion",
        help="Which mapped swagger spec should be generated.",
    )
    parser.add_argument(
        "--spec-url",
        help="Optional override of the swagger URL (keeps the mapped filename).",
    )
    parser.add_argument(
        "--spec-filename",
        help="Optional override of the swagger filename (saved under each version).",
    )
    parser.add_argument(
        "--package-name",
        help="Optional override of the generated package name inside the version folder.",
    )
    parser.add_argument(
        "--target-root",
        type=Path,
        help="Optional override of the target root where versioned folders are created.",
    )
    parser.add_argument(
        "--force-version",
        type=int,
        help="Explicit version number to create (default: next available vN).",
    )
    parser.add_argument(
        "--meta",
        default="none",
        help="Meta type passed to openapi-python-client (default: none).",
    )
    parser.add_argument(
        "--python-cmd",
        default="openapi-python-client",
        help="Command used to invoke the OpenAPI client generator.",
    )
    parser.add_argument(
        "--check-spec-changed",
        action="store_true",
        help="Check remote spec fingerprint against latest spec.lock.json and exit without generation.",
    )
    parser.add_argument(
        "--use-cached-spec",
        action="store_true",
        help="Use existing swagger/<spec>.yaml from --force-version and skip downloading.",
    )
    return parser.parse_args()


def determine_next_version(target_root: Path, force_version: int | None) -> int:
    if force_version is not None:
        return force_version
    version_dirs = iter_version_dirs(target_root)
    highest = max((int(version_dir.name[1:]) for version_dir in version_dirs), default=0)
    return highest + 1


def iter_version_dirs(target_root: Path) -> list[Path]:
    if not target_root.exists():
        return []
    version_dirs = [
        entry
        for entry in target_root.iterdir()
        if entry.is_dir() and entry.name.startswith("v") and entry.name[1:].isdigit()
    ]
    version_dirs.sort(key=lambda p: int(p.name[1:]), reverse=True)
    return version_dirs


def find_latest_lock(target_root: Path) -> tuple[Path, dict[str, str | int]] | None:
    for version_dir in iter_version_dirs(target_root):
        swagger_dir = version_dir / "swagger"
        lock_file = lock_path_for(swagger_dir)
        if lock_file.exists():
            return lock_file, read_spec_lock(lock_file)
    return None


def main() -> int:
    args = parse_args()
    target_key = args.spec_key
    config = SWAGGER_TARGETS[target_key]

    target_root = args.target_root or config.target_root
    target_root.mkdir(parents=True, exist_ok=True)

    spec_url = args.spec_url or config.spec_url
    spec_filename = args.spec_filename or config.spec_filename
    package_name = args.package_name or config.package_name

    if args.check_spec_changed:
        latest_lock = find_latest_lock(target_root)
        if latest_lock is None:
            print(
                f"No spec.lock.json found under {target_root} for --check-spec-changed.",
                file=sys.stderr,
            )
            return 1
        lock_file, lock_data = latest_lock
        if lock_data.get("spec_filename") != spec_filename:
            print(
                f"Latest lock {lock_file} references another spec_filename={lock_data.get('spec_filename')!r}.",
                file=sys.stderr,
            )
            return 1
        try:
            remote_bytes = fetch_spec_bytes(spec_url)
        except Exception as exc:
            print(f"Failed to fetch remote spec: {exc}", file=sys.stderr)
            return 1
        remote_sha = compute_sha256(remote_bytes)
        remote_size = len(remote_bytes)
        locked_sha = str(lock_data.get("sha256", ""))
        locked_size = int(lock_data.get("size_bytes", -1))
        changed = remote_sha != locked_sha or remote_size != locked_size
        print(
            "\n".join(
                [
                    f"lock_file={lock_file}",
                    f"remote_sha256={remote_sha}",
                    f"remote_size_bytes={remote_size}",
                    f"locked_sha256={locked_sha}",
                    f"locked_size_bytes={locked_size}",
                    f"changed={'true' if changed else 'false'}",
                ]
            ),
            file=sys.stderr,
        )
        return 10 if changed else 0

    version = determine_next_version(target_root, args.force_version)
    target_dir = target_root / f"v{version}"
    if target_dir.exists() and not args.use_cached_spec:
        raise SystemExit(f"Target directory {target_dir} already exists. Remove it or pass --force-version <new-number>.")

    swagger_dir = target_dir / "swagger"
    spec_path = swagger_dir / spec_filename
    translit_spec_path = spec_path.with_name(f"{spec_path.stem}-translit{spec_path.suffix}")
    lock_path = lock_path_for(swagger_dir)

    package_root = target_dir / package_name

    if args.use_cached_spec:
        if args.force_version is None:
            raise SystemExit("--use-cached-spec requires --force-version pointing to an existing vN.")
        if not target_dir.exists():
            raise SystemExit(f"--use-cached-spec expects existing version directory: {target_dir}")
        if not spec_path.exists():
            raise SystemExit(f"Cached spec not found: {spec_path}")
        if not lock_path.exists():
            raise SystemExit(f"Cached spec lock not found: {lock_path}")
        lock_data = read_spec_lock(lock_path)
        if lock_data.get("spec_filename") != spec_filename:
            raise SystemExit(
                f"Cached lock spec_filename={lock_data.get('spec_filename')!r} "
                f"does not match requested {spec_filename!r}."
            )
        cached_bytes = spec_path.read_bytes()
        current_sha = compute_sha256(cached_bytes)
        locked_sha = str(lock_data.get("sha256", ""))
        if current_sha != locked_sha:
            raise SystemExit(
                f"Cached spec hash mismatch for {spec_path}: current={current_sha} locked={locked_sha}."
            )
        spec_bytes = cached_bytes
    else:
        target_dir.mkdir(parents=True, exist_ok=False)
        target_dir.joinpath("__init__.py").write_text("")
        swagger_dir.mkdir(parents=True, exist_ok=True)
        spec_bytes = fetch_spec_bytes(spec_url)
        spec_path.write_bytes(spec_bytes)
        lock_data = build_spec_lock(
            spec_key=target_key,
            spec_url=spec_url,
            spec_filename=spec_filename,
            spec_bytes=spec_bytes,
            generator=args.python_cmd,
            generator_meta=args.meta,
        )
        write_spec_lock(lock_path, lock_data)

    spec_sha = compute_sha256(spec_bytes)
    spec_size = len(spec_bytes)

    if config.skip_transliteration:
        spec_for_generator = spec_path
    else:
        translit_script = (REPO_ROOT / "scripts" / "translit_yaml.py").resolve()
        run_transliteration(translit_script, spec_path, translit_spec_path)
        spec_for_generator = translit_spec_path

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        run_generator(spec_for_generator, temp_path, args.meta, args.python_cmd)
        package_root.mkdir(parents=True, exist_ok=True)
        copy_generated_contents(temp_path, package_root)

    msg_lines = [
        "Client generation succeeded.",
        f"Spec saved to {spec_path}",
        f"Spec lock: {lock_path}",
        f"Spec sha256: {spec_sha}",
        f"Spec size_bytes: {spec_size}",
        f"Using cached spec: {'true' if args.use_cached_spec else 'false'}",
        f"Generated package placed under {package_root}",
        f"Client version: v{version} (spec key: {target_key})",
    ]
    if not config.skip_transliteration:
        msg_lines.insert(2, f"Transliterated spec saved to {translit_spec_path}")
    print("\n".join(msg_lines), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
