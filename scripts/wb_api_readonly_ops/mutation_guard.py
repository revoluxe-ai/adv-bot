"""READ_ONLY_NO_MUTATION: denylist mutation/finance write surfaces для этого entrypoint."""

from __future__ import annotations

# Имена операций, которые ops-скрипт этого класса MUST NOT вызывать.
MUTATION_WRITE_OPS: frozenset[str] = frozenset(
    {
        "start_campaign",
        "pause_campaign",
        "stop_campaign",
        "rename_campaign",
        "set_cluster_bids",
        "set_common_bids",
        "patch_adv_v1_bids",
        "top_up_budget",
        "set_auction_placement",
        "set_minus_phrases",
        "create_campaign",
        "delete_campaign",
        # finance / wallet — вне readonly ORDERS surface (INC-RO-06)
        "get_balance",
        "get_payments",
        "create_payout",
        "wallet_top_up",
    }
)


class MutationWriteRefused(PermissionError):
    """Попытка mutation write из read-only ops entrypoint."""


def assert_read_only_op(op_name: str) -> None:
    """Отказать, если op_name в denylist mutation/finance writes."""
    if op_name in MUTATION_WRITE_OPS:
        raise MutationWriteRefused(
            f"READ_ONLY_NO_MUTATION: refused op {op_name!r} for wb_api_readonly_ops"
        )
