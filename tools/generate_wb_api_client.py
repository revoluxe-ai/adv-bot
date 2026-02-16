"""Generate a WB API client package from the Wildberries OpenAPI specification."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


def download_spec(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "wb-api-client-generator/1.0"})
    with urlopen(request) as response:
        data = response.read()
    destination.write_bytes(data)


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
    "products": SwaggerTarget(
        key="products",
        spec_url="https://dev.wildberries.ru/api/swagger/yaml/ru/02-products.yaml",
        spec_filename="02-products.yaml",
        target_root=REPO_ROOT / "app" / "core" / "mp" / "wb" / "api" / "generated" / "products",
        package_name="content_products_client",
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
    return parser.parse_args()


def determine_next_version(target_root: Path, force_version: int | None) -> int:
    if force_version is not None:
        return force_version
    versions: list[int] = []
    if target_root.exists():
        for entry in target_root.iterdir():
            if entry.is_dir() and entry.name.startswith("v") and entry.name[1:].isdigit():
                versions.append(int(entry.name[1:]))
    highest = max(versions, default=0)
    return highest + 1


def main() -> int:
    args = parse_args()
    target_key = args.spec_key
    config = SWAGGER_TARGETS[target_key]

    target_root = args.target_root or config.target_root
    target_root.mkdir(parents=True, exist_ok=True)

    spec_url = args.spec_url or config.spec_url
    spec_filename = args.spec_filename or config.spec_filename
    package_name = args.package_name or config.package_name

    version = determine_next_version(target_root, args.force_version)
    target_dir = target_root / f"v{version}"
    if target_dir.exists():
        raise SystemExit(f"Target directory {target_dir} already exists. Remove it or pass --force-version <new-number>.")

    swagger_dir = target_dir / "swagger"
    spec_path = swagger_dir / spec_filename
    translit_spec_path = spec_path.with_name(f"{spec_path.stem}-translit{spec_path.suffix}")

    package_root = target_dir / package_name

    target_dir.mkdir(parents=True, exist_ok=False)
    target_dir.joinpath("__init__.py").write_text("")
    swagger_dir.mkdir(parents=True, exist_ok=True)

    download_spec(spec_url, spec_path)

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
        f"Generated package placed under {package_root}",
        f"Client version: v{version} (spec key: {target_key})",
    ]
    if not config.skip_transliteration:
        msg_lines.insert(2, f"Transliterated spec saved to {translit_spec_path}")
    print("\n".join(msg_lines), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
