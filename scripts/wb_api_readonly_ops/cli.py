"""Argparse для wb_api_readonly_ops.

Spec: Explicit contract and artifact-class CLI surface
(wb-api-read-only-preflight / wb-readonly-contract-preflight-return).
"""

from __future__ import annotations

import argparse

from scripts.wb_api_readonly_ops.contract_constants import (
    CONTRACT_ID,
    DEFAULT_BOUND_ALIAS,
    DEFAULT_PERIOD_END,
    DEFAULT_PERIOD_START,
)
from scripts.wb_api_readonly_ops.r04_constants import CONTRACT_ID_R04
from scripts.wb_api_readonly_ops.r04_003_constants import CONTRACT_ID_R04_003
from scripts.wb_api_readonly_ops.r04_003b_constants import CONTRACT_ID_R04_003B
from scripts.wb_api_readonly_ops.models import (
    ORDERS_PERIOD_DATE_FROM_DEFAULT,
    ArtifactClass,
    Mode,
)

DEFAULT_MAX_SECONDS = 180.0
DEFAULT_MAX_CALLS = 40
DEFAULT_COLLECT_MAX_SECONDS = 3600.0
DEFAULT_COLLECT_MAX_API_CALLS = 10_000
DEFAULT_FUNNEL_NMID_BATCH = 20
DEFAULT_CARDS_PAGE_LIMIT = 100


def build_parser() -> argparse.ArgumentParser:
    """CLI: обязательные --shop-id и --mode; опциональный contract surface."""
    parser = argparse.ArgumentParser(
        prog="wb_api_readonly_ops",
        description=(
            "Owner-local WB API read-only preflight/collect via existing stack. "
            "Contracts: COL-R03-009 or COL-R04-001 with --artifact-class "
            "contract_preflight. Not Web READ_ONLY_PREFLIGHT_PASS. "
            "Local Cursor must not call production cabinet/API."
        ),
    )
    parser.add_argument(
        "--shop-id",
        required=True,
        help="WB cabinet shop_id (never hardcoded; never in RETURN zip)",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=[Mode.PREFLIGHT.value, Mode.COLLECT.value],
        help="preflight=smallest probe; collect=best-effort pull",
    )
    parser.add_argument(
        "--contract",
        default=None,
        choices=[
            CONTRACT_ID,
            CONTRACT_ID_R04,
            CONTRACT_ID_R04_003,
            CONTRACT_ID_R04_003B,
        ],
        help=(
            f"Frozen contract id ({CONTRACT_ID}, {CONTRACT_ID_R04}, "
            f"{CONTRACT_ID_R04_003}, or {CONTRACT_ID_R04_003B} orders fix)"
        ),
    )
    parser.add_argument(
        "--artifact-class",
        default=None,
        choices=[c.value for c in ArtifactClass],
        help=(
            "contract_preflight=COL-R03-009 RETURN primary; "
            "l0_research=Owner-local research zip; "
            "clean_dump=requires READ_ONLY_PREFLIGHT_PASS accept file"
        ),
    )
    parser.add_argument(
        "--bound-alias",
        default=DEFAULT_BOUND_ALIAS,
        help="Account alias for contract attestations (default WB-TEST-CABINET-001)",
    )
    parser.add_argument(
        "--period-start",
        default=DEFAULT_PERIOD_START,
        help="Contract period start YYYY-MM-DD (Europe/Moscow calendar)",
    )
    parser.add_argument(
        "--period-end",
        default=DEFAULT_PERIOD_END,
        help="Contract period end YYYY-MM-DD (Europe/Moscow calendar)",
    )
    parser.add_argument(
        "--require-preflight-pass",
        default=None,
        help=(
            "Path to accept file that must contain READ_ONLY_PREFLIGHT_PASS=YES "
            "(required for artifact-class clean_dump)"
        ),
    )
    parser.add_argument(
        "--emit-l0-side",
        action="store_true",
        help="With contract_preflight, also write L0 research zip as side artifact",
    )
    parser.add_argument(
        "--orders-date-from",
        default=ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat(),
        help=(
            "ORDERS family dateFrom (YYYY-MM-DD, Moscow calendar). "
            f"Default pilot {ORDERS_PERIOD_DATE_FROM_DEFAULT.isoformat()}; "
            "NOT yesterday→today (analytics may still use that)."
        ),
    )
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=DEFAULT_MAX_SECONDS,
        help="run ceiling wall-clock seconds (default 180)",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=DEFAULT_MAX_CALLS,
        help="run ceiling family API calls (default 40; preflight orchestrator)",
    )
    parser.add_argument(
        "--max-api-calls",
        type=int,
        default=DEFAULT_COLLECT_MAX_API_CALLS,
        help=(
            "collect mode: max WB API calls for pagination/batching "
            f"(default {DEFAULT_COLLECT_MAX_API_CALLS})"
        ),
    )
    parser.add_argument(
        "--ads-date-from",
        default=None,
        help="collect mode: ads/fullstats/normquery start YYYY-MM-DD (default from orders)",
    )
    parser.add_argument(
        "--ads-date-to",
        default=None,
        help="collect mode: ads/fullstats/normquery end YYYY-MM-DD (default today)",
    )
    parser.add_argument(
        "--funnel-nmid-batch-size",
        type=int,
        default=DEFAULT_FUNNEL_NMID_BATCH,
        help=f"collect mode: nmIDs per funnel request (default {DEFAULT_FUNNEL_NMID_BATCH})",
    )
    parser.add_argument(
        "--cards-page-limit",
        type=int,
        default=DEFAULT_CARDS_PAGE_LIMIT,
        help=f"collect mode: cards list page size (default {DEFAULT_CARDS_PAGE_LIMIT})",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="override outputs dir (default scripts/wb_api_readonly_ops/outputs)",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать argv; unknown mode → SystemExit non-zero via argparse."""
    return build_parser().parse_args(argv)


def resolve_artifact_class(args: argparse.Namespace) -> ArtifactClass | None:
    """Вывести ArtifactClass из --artifact-class / --contract.

    Spec: contract COL-R03-009 или artifact-class contract_preflight →
    contract path; иначе None (legacy L0) или явный l0_research/clean_dump.
    """
    if args.artifact_class:
        return ArtifactClass(args.artifact_class)
    if args.contract in (
        CONTRACT_ID,
        CONTRACT_ID_R04,
        CONTRACT_ID_R04_003,
        CONTRACT_ID_R04_003B,
    ):
        return ArtifactClass.CONTRACT_PREFLIGHT
    return None
