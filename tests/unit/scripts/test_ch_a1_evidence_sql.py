"""Regression tests for bound SQL parameters in the A1 evidence collector."""

from __future__ import annotations

from scripts import ch_a1_evidence as evidence


def test_malicious_shop_id_is_bound_for_postgres_and_clickhouse() -> None:
    """Runtime shop identity never becomes SQL source text."""
    malicious_shop_id = "shop'; DROP TABLE public.wbcabinet; --"

    pg_filter, _, _, pg_params = evidence.filter_for_postgres(
        ["shop_id"],
        set(),
        set(),
        set(),
        set(),
        shop_id=malicious_shop_id,
    )
    ch_filter, _, ch_params = evidence.filter_for_clickhouse(
        [{"name": "shop_id"}],
        set(),
        set(),
        set(),
        shop_id=malicious_shop_id,
    )

    assert pg_filter == '"shop_id" = $1'
    assert malicious_shop_id not in pg_filter
    assert pg_params == (malicious_shop_id,)
    assert ch_filter == "`shop_id` = {shop_id:String}"
    assert malicious_shop_id not in ch_filter
    assert ch_params == {"shop_id": malicious_shop_id}


def test_runtime_identifier_lists_use_bind_parameters() -> None:
    """Cabinet, campaign, and NMID values are not interpolated into SQL."""
    pg_filter, _, _, pg_params = evidence.filter_for_postgres(
        ["wb_cabinet_id", "adv_setting_id", "adv_id", "nmid"],
        {401},
        {32824944},
        {10749810},
        {1256595631},
        shop_id="unused",
    )

    assert pg_filter == (
        '("wb_cabinet_id" IN ($1)) OR ("adv_setting_id" IN ($2)) '
        'OR ("adv_id" IN ($3)) OR ("nmid" IN ($4))'
    )
    assert pg_params == (401, 32824944, 10749810, 1256595631)

    ch_filter, _, ch_params = evidence.filter_for_clickhouse(
        [
            {"name": "cabinet_id"},
            {"name": "adv_id"},
            {"name": "nmid"},
        ],
        {401},
        {10749810},
        {1256595631},
        shop_id="unused",
    )
    assert "401" not in ch_filter
    assert "10749810" not in ch_filter
    assert "1256595631" not in ch_filter
    assert ch_params == {
        "cabinet_id_0": 401,
        "adv_id_0": 10749810,
        "nmid_0": 1256595631,
    }


def test_direct_postgres_queries_bind_shop_and_cabinet_values() -> None:
    """Direct mapping queries also keep runtime values out of SQL text."""
    malicious_shop_id = "shop'; DROP TABLE public.wbcabinet; --"
    cabinet_query, cabinet_params = evidence._build_wbcabinet_query(
        ["id", "shop_id"],
        malicious_shop_id,
    )
    setting_query, setting_params = evidence._build_advsetting_query(
        ["id", "wb_cabinet_id"],
        {401, 402},
    )

    assert malicious_shop_id not in cabinet_query
    assert cabinet_query.endswith('"shop_id" = $1')
    assert cabinet_params == (malicious_shop_id,)
    assert setting_query.endswith('"wb_cabinet_id" IN ($1, $2)')
    assert setting_params == (401, 402)


def test_postgres_filter_has_four_value_contract_for_all_column_shapes() -> None:
    """Sensitive, ordinary, and empty projections share one return shape."""
    all_sensitive = evidence.filter_for_postgres(
        ["password", "api_token"],
        {401},
        set(),
        set(),
        set(),
        shop_id="unused",
    )
    ordinary = evidence.filter_for_postgres(
        ["wb_cabinet_id", "password"],
        {401},
        set(),
        set(),
        set(),
        shop_id="unused",
    )
    empty = evidence.filter_for_postgres(
        [],
        set(),
        set(),
        set(),
        set(),
        shop_id="unused",
    )

    assert len(all_sensitive) == len(ordinary) == len(empty) == 4
    assert all_sensitive == (None, "all columns are sensitive", [], ())
    assert ordinary[2] == ["wb_cabinet_id"]
    assert ordinary[3] == (401,)
    assert empty == (None, "all columns are sensitive", [], ())
