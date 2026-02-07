"""Entry point for pyright-strict: runs pyright with pyrightconfig_strict.json."""

import sys


def main() -> None:
    args = ["--project", "pyrightconfig_strict.json"] + sys.argv[1:]
    from pyright import cli

    sys.exit(cli.main(args))
