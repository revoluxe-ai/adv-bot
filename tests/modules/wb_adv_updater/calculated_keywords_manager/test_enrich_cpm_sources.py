"""Tests for __enrich_pre_calculated_with_cpm_sources: all four CPM sources and resolved_cpm cascade."""

from datetime import datetime

import pytest

from app.modules.cpm_sources_resolver.dto import AllCpmSourcesPerText
from app.modules.wb_adv_updater.calculated_keywords_manager.calculated_keywords_manager import (
    CalculatedKeywordsManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import (
    KeywordCpmSources,
)
from tests.factories.keyword_pipeline import (
    KeywordSettingDTOFactory,
    KeywordStatFactory,
    PreCalculatedKeywordFactory,
)


def test_enrich_fills_all_four_sources_and_resolved_cpm_cascade() -> None:
    """When all_sources_by_text has set_bid, api, bid_log and cluster_stat has cpm, all four fields are set; resolved_cpm follows set_bid → api → bid_log → stats."""
    text = "платье"
    ts = datetime(2025, 3, 1, 12, 0)
    pre_kw = PreCalculatedKeywordFactory(
        keyword_setting=KeywordSettingDTOFactory(text=text),
        cluster_stat=KeywordStatFactory(norm_query=text, cpm=50.0),
    )
    all_sources = {
        text: AllCpmSourcesPerText(
            text=text,
            cpm_set_bid=100,
            cpm_set_bid_date=ts,
            cpm_from_api=90,
            cpm_from_bid_log=80.0,
            cpm_from_bid_log_date=ts,
        ),
    }
    enriched = CalculatedKeywordsManager._CalculatedKeywordsManager__enrich_pre_calculated_with_cpm_sources(
        [pre_kw], all_sources
    )
    assert len(enriched) == 1
    sources = enriched[0].cpm_sources
    assert sources is not None
    assert sources.cpm_set_bid == 100
    assert sources.cpm_set_bid_date == ts
    assert sources.cpm_from_api == 90
    assert sources.cpm_from_bid_log == 80.0
    assert sources.cpm_from_bid_log_date == ts
    assert sources.cpm_from_stats == 50.0
    assert sources.cpm_from_stats_date is None
    assert sources.resolved_cpm() == 100.0  # set_bid wins


def test_enrich_resolved_cpm_api_when_no_set_bid() -> None:
    """resolved_cpm returns api when set_bid is None."""
    text = "куртка"
    pre_kw = PreCalculatedKeywordFactory(
        keyword_setting=KeywordSettingDTOFactory(text=text),
        cluster_stat=KeywordStatFactory(norm_query=text, cpm=40.0),
    )
    all_sources = {
        text: AllCpmSourcesPerText(
            text=text,
            cpm_set_bid=None,
            cpm_set_bid_date=None,
            cpm_from_api=75,
            cpm_from_bid_log=60.0,
            cpm_from_bid_log_date=None,
        ),
    }
    enriched = CalculatedKeywordsManager._CalculatedKeywordsManager__enrich_pre_calculated_with_cpm_sources(
        [pre_kw], all_sources
    )
    assert enriched[0].cpm_sources.resolved_cpm() == 75.0


def test_enrich_resolved_cpm_stats_when_only_stats() -> None:
    """When sources_row is missing, only cpm_from_stats from cluster_stat is set."""
    text = "шапка"
    pre_kw = PreCalculatedKeywordFactory(
        keyword_setting=KeywordSettingDTOFactory(text=text),
        cluster_stat=KeywordStatFactory(norm_query=text, cpm=30.0),
    )
    all_sources: dict[str, AllCpmSourcesPerText] = {}
    enriched = CalculatedKeywordsManager._CalculatedKeywordsManager__enrich_pre_calculated_with_cpm_sources(
        [pre_kw], all_sources
    )
    sources = enriched[0].cpm_sources
    assert sources is not None
    assert sources.cpm_set_bid is None
    assert sources.cpm_from_api is None
    assert sources.cpm_from_bid_log is None
    assert sources.cpm_from_stats == 30.0
    assert sources.resolved_cpm() == 30.0
