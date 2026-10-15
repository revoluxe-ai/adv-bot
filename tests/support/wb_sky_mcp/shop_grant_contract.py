"""ContractCase vectors for ``ShopGrantReader.list_shops`` parity."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.wb_sky_mcp.grants import ShopGrant, ShopGrantReader

CONTRACT_ID = "wb_sky_mcp.shop_grant.pg_boundary.v1"


@dataclass(frozen=True)
class ShopGrantContractCase:
    """Expected grant list shape for a principal."""

    case_id: str
    user_id: int
    expected_shop_ids: tuple[str, ...]


def assert_shop_grants_match(
    grants: list[ShopGrant],
    *,
    expected_shop_ids: tuple[str, ...],
) -> None:
    """Memory and SQL readers must expose the same shop_id set and fields."""
    assert [g.shop_id for g in grants] == list(expected_shop_ids)
    for grant in grants:
        assert isinstance(grant.name, str)
        assert isinstance(grant.active, bool)


async def run_shop_grant_contract(
    reader: ShopGrantReader,
    case: ShopGrantContractCase,
) -> list[ShopGrant]:
    """Load shops for ``case.user_id`` and assert canonical shape."""
    grants = await reader.list_shops(case.user_id)
    assert_shop_grants_match(grants, expected_shop_ids=case.expected_shop_ids)
    return grants
