"""CLI for campaign settings history updater.

Examples:
  python -m app.modules.campaign_settings_history once
  python -m app.modules.campaign_settings_history daemon

Writes are disabled unless CAMPAIGN_SETTINGS_HISTORY_ENABLED=1.
DDL is never executed here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict

from .config import CampaignSettingsHistoryConfig
from .updater import CampaignSettingsHistoryUpdater


async def run_once_from_config(
    config: CampaignSettingsHistoryConfig | None = None,
):
    cfg = config or CampaignSettingsHistoryConfig.from_env()
    updater = CampaignSettingsHistoryUpdater(
        interval_seconds=cfg.interval_seconds,
        enabled=cfg.enabled,
    )
    return await updater.run_once()


async def run_daemon_from_config(
    config: CampaignSettingsHistoryConfig | None = None,
) -> None:
    cfg = config or CampaignSettingsHistoryConfig.from_env()
    updater = CampaignSettingsHistoryUpdater(
        interval_seconds=cfg.interval_seconds,
        enabled=cfg.enabled,
    )
    await updater.run_forever()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="campaign-settings-history",
        description=(
            "Observe current PostgreSQL campaign settings and append changed "
            "canonical snapshots to ClickHouse. No DDL/WB/settings writes."
        ),
    )
    parser.add_argument("command", choices=("once", "daemon"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "once":
        result = asyncio.run(run_once_from_config())
        print(json.dumps(asdict(result), sort_keys=True))
        return 0 if result.code in {"ok", "disabled"} else 1

    asyncio.run(run_daemon_from_config())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
