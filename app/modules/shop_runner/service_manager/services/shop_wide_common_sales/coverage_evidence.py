"""Redis evidence для last-attempt coverage shop-wide common-sales."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

from app.core.redis_manager_v2.redis_client import RedisClient

from .collect_types import CoverageStatus

logger = logging.getLogger(__name__)

AttemptStatus = Literal["STARTED", "COMPLETE", "PARTIAL", "FAILED"]
VALID_ATTEMPT_STATUSES: frozenset[str] = frozenset(
    {"STARTED", "COMPLETE", "PARTIAL", "FAILED"}
)
EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_SCOPE = "current_non_trash_cards"
EVIDENCE_SOURCE = "wb_sales_funnel_products_history"
# WB DTO field names imply RUB; source currency is not certified in this change.
METRICS_SOURCE_CURRENCY = "unknown"
STORE_DRR_NUMERATOR_STATUS = "BLOCKED_BY_CAMPAIGN_COVERAGE"

LAST_ATTEMPT_TTL_SEC = 600
TRANSITION_TTL_SEC = 600


@dataclass
class LastAttemptEvidence:
    """JSON-снимок последней попытки сбора для shop_id."""

    attempt_status: AttemptStatus
    window_start: str
    window_end: str
    a_count: int
    e_count: int
    u_count: int
    assortment_complete: bool
    assortment_pages: int
    expected_pair_count: int
    returned_pair_count: int
    persisted_pair_count: int
    missing_pair_count: int
    rejected_pair_count: int
    partial_reason: str | None
    tick_ts: str
    schema_version: int = EVIDENCE_SCHEMA_VERSION
    attempt_id: str = ""
    scope: str = EVIDENCE_SCOPE
    source: str = EVIDENCE_SOURCE
    assortment_hash: str = ""
    provisional: bool = False


class ShopWideCoverageEvidenceStore:
    """Минимальное хранилище last-attempt и transition snapshot в Redis."""

    _LAST_ATTEMPT_PREFIX = "shop_wide_common_sales:last_attempt"
    _TRANSITION_PREFIX = "shop_wide_common_sales:transition"

    def __init__(self, redis_client: RedisClient) -> None:
        self._redis = redis_client

    @classmethod
    def last_attempt_key(cls, shop_id: str) -> str:
        return f"{cls._LAST_ATTEMPT_PREFIX}:{shop_id}"

    @classmethod
    def transition_key(cls, shop_id: str) -> str:
        return f"{cls._TRANSITION_PREFIX}:{shop_id}"

    def new_attempt_id(self) -> str:
        """Уникальный attempt_id для одного тика (STARTED → terminal)."""
        return uuid.uuid4().hex

    async def write_provisional_started(
        self,
        shop_id: str,
        *,
        attempt_id: str,
        window_start: str,
        window_end: str,
    ) -> None:
        """
        Записать provisional STARTED в начале тика до Content API / legacy await.

        Инвалидирует prior COMPLETE; A/E/U counts unknown (0), assortment incomplete.
        """
        evidence = LastAttemptEvidence(
            attempt_status="STARTED",
            window_start=window_start,
            window_end=window_end,
            a_count=0,
            e_count=0,
            u_count=0,
            assortment_complete=False,
            assortment_pages=0,
            expected_pair_count=0,
            returned_pair_count=0,
            persisted_pair_count=0,
            missing_pair_count=0,
            rejected_pair_count=0,
            partial_reason=None,
            tick_ts=datetime.now(UTC).isoformat(),
            schema_version=EVIDENCE_SCHEMA_VERSION,
            attempt_id=attempt_id,
            scope=EVIDENCE_SCOPE,
            source=EVIDENCE_SOURCE,
            assortment_hash="",
            provisional=True,
        )
        await self._write_last_attempt(shop_id, evidence)

    async def enrich_started(
        self,
        shop_id: str,
        *,
        attempt_id: str,
        window_start: str,
        window_end: str,
        a_count: int,
        e_count: int,
        u_count: int,
        assortment_complete: bool,
        assortment_pages: int,
        assortment_hash: str,
    ) -> None:
        """Обогатить STARTED тем же attempt_id после известного A/E/U partition."""
        evidence = LastAttemptEvidence(
            attempt_status="STARTED",
            window_start=window_start,
            window_end=window_end,
            a_count=a_count,
            e_count=e_count,
            u_count=u_count,
            assortment_complete=assortment_complete,
            assortment_pages=assortment_pages,
            expected_pair_count=a_count * 7,
            returned_pair_count=0,
            persisted_pair_count=0,
            missing_pair_count=a_count * 7,
            rejected_pair_count=0,
            partial_reason=None,
            tick_ts=datetime.now(UTC).isoformat(),
            schema_version=EVIDENCE_SCHEMA_VERSION,
            attempt_id=attempt_id,
            scope=EVIDENCE_SCOPE,
            source=EVIDENCE_SOURCE,
            assortment_hash=assortment_hash,
            provisional=False,
        )
        await self._write_last_attempt(shop_id, evidence)

    async def write_started(
        self,
        shop_id: str,
        *,
        attempt_id: str,
        window_start: str,
        window_end: str,
        a_count: int,
        e_count: int,
        u_count: int,
        assortment_complete: bool,
        assortment_pages: int,
        assortment_hash: str,
    ) -> None:
        """Записать STARTED перед первым funnel API (enriched partition)."""
        await self.enrich_started(
            shop_id,
            attempt_id=attempt_id,
            window_start=window_start,
            window_end=window_end,
            a_count=a_count,
            e_count=e_count,
            u_count=u_count,
            assortment_complete=assortment_complete,
            assortment_pages=assortment_pages,
            assortment_hash=assortment_hash,
        )

    async def write_terminal(
        self,
        shop_id: str,
        evidence: LastAttemptEvidence,
    ) -> None:
        """Записать terminal state (COMPLETE/PARTIAL/FAILED) после оценки тика."""
        await self._write_last_attempt(shop_id, evidence)

    async def read_last_attempt(self, shop_id: str) -> LastAttemptEvidence | None:
        raw = await self._redis.get(self.last_attempt_key(shop_id))
        if raw is None:
            return None
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            logger.debug("malformed last_attempt JSON shop_id=%s", shop_id)
            return None
        if not isinstance(parsed, dict):
            logger.debug("last_attempt not dict shop_id=%s", shop_id)
            return None
        data = cast(dict[str, Any], parsed)
        if data.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
            logger.debug(
                "unsupported schema_version=%s shop_id=%s",
                data.get("schema_version"),
                shop_id,
            )
            return None
        if data.get("scope") != EVIDENCE_SCOPE:
            logger.debug("invalid scope shop_id=%s", shop_id)
            return None
        if data.get("source") != EVIDENCE_SOURCE:
            logger.debug("invalid source shop_id=%s", shop_id)
            return None
        attempt_status = data.get("attempt_status")
        if attempt_status not in VALID_ATTEMPT_STATUSES:
            logger.debug(
                "invalid attempt_status=%s shop_id=%s",
                attempt_status,
                shop_id,
            )
            return None
        if data.get("provisional") is True and attempt_status == "COMPLETE":
            logger.debug("provisional COMPLETE rejected shop_id=%s", shop_id)
            return None
        if not isinstance(data.get("assortment_complete"), bool):
            logger.debug("invalid assortment_complete shop_id=%s", shop_id)
            return None
        provisional = data.get("provisional")
        if provisional is not None and not isinstance(provisional, bool):
            logger.debug("invalid provisional shop_id=%s", shop_id)
            return None
        for str_field in ("window_start", "window_end", "tick_ts", "attempt_id", "assortment_hash"):
            value = data.get(str_field)
            if not isinstance(value, str):
                logger.debug("invalid %s shop_id=%s", str_field, shop_id)
                return None
        for int_field in (
            "a_count",
            "e_count",
            "u_count",
            "assortment_pages",
            "expected_pair_count",
            "returned_pair_count",
            "persisted_pair_count",
            "missing_pair_count",
            "rejected_pair_count",
        ):
            value = data.get(int_field)
            if not isinstance(value, int) or isinstance(value, bool):
                logger.debug("invalid %s shop_id=%s", int_field, shop_id)
                return None
        partial_reason = data.get("partial_reason")
        if partial_reason is not None and not isinstance(partial_reason, str):
            logger.debug("invalid partial_reason shop_id=%s", shop_id)
            return None
        a_count = data["a_count"]
        u_count = data["u_count"]
        if u_count > a_count:
            logger.debug("u_count > a_count shop_id=%s", shop_id)
            return None
        expected = data["expected_pair_count"]
        returned = data["returned_pair_count"]
        persisted = data["persisted_pair_count"]
        missing = data["missing_pair_count"]
        if expected != a_count * 7:
            logger.debug("expected_pair_count mismatch shop_id=%s", shop_id)
            return None
        if missing != max(0, expected - persisted):
            logger.debug("missing_pair_count mismatch shop_id=%s", shop_id)
            return None
        if returned < persisted:
            logger.debug("returned < persisted shop_id=%s", shop_id)
            return None
        try:
            return LastAttemptEvidence(**data)
        except TypeError:
            logger.debug("invalid last_attempt fields shop_id=%s", shop_id)
            return None

    async def write_transition_snapshot(
        self,
        shop_id: str,
        *,
        attempt_id: str,
        a_nmids: frozenset[int],
        e_nmids: frozenset[int],
        u_nmids: frozenset[int],
    ) -> None:
        """Сохранить sorted hashes A/E/U + attempt_id для transition-логов."""
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "attempt_id": attempt_id,
            "scope": EVIDENCE_SCOPE,
            "source": EVIDENCE_SOURCE,
            "a_hash": _sorted_hash(a_nmids),
            "e_hash": _sorted_hash(e_nmids),
            "u_hash": _sorted_hash(u_nmids),
            "ts": datetime.now(UTC).isoformat(),
        }
        await self._redis.set(
            self.transition_key(shop_id),
            json.dumps(payload, ensure_ascii=False),
            ex=TRANSITION_TTL_SEC,
        )

    async def _write_last_attempt(
        self,
        shop_id: str,
        evidence: LastAttemptEvidence,
    ) -> None:
        await self._redis.set(
            self.last_attempt_key(shop_id),
            json.dumps(asdict(evidence), ensure_ascii=False),
            ex=LAST_ATTEMPT_TTL_SEC,
        )


def derive_attempt_status(coverage_status: CoverageStatus) -> AttemptStatus:
    """Сопоставить coverage_status тика с attempt_status Redis."""
    if coverage_status == CoverageStatus.COMPLETE:
        return "COMPLETE"
    if coverage_status == CoverageStatus.FAILED:
        return "FAILED"
    return "PARTIAL"


def sorted_nmids_hash(nmids: frozenset[int]) -> str:
    """SHA256 prefix по sorted nmIDs для evidence binding."""
    joined = ",".join(str(n) for n in sorted(nmids))
    return hashlib.sha256(joined.encode()).hexdigest()[:16]


def _sorted_hash(nmids: frozenset[int]) -> str:
    return sorted_nmids_hash(nmids)
