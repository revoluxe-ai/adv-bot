"""Детерминированный observation_id по полному semantic content наблюдения."""

from __future__ import annotations

import hashlib
import json

from app.modules.attribution_facts.domain.models import AttributionCommerceFact


def semantic_observation_id(fact: AttributionCommerceFact) -> str:
    """
    Content-hash observation identity (без ingested_at / source_revision).

    Идентичный semantic replay → тот же id; любая semantic correction → новый id.
    """
    metrics = fact.metrics
    gmv_token: str | None
    if metrics.attributed_gmv_rub is None:
        gmv_token = None
    else:
        gmv_token = format(metrics.attributed_gmv_rub, "f")
    payload = {
        "shop_id": fact.key.shop_id,
        "physical_adv_id": fact.key.physical_adv_id,
        "event_date": fact.key.event_date.isoformat(),
        "app_type": fact.key.app_type,
        "ordered_nm_id": fact.key.ordered_nm_id,
        "source_family": str(fact.key.source_family),
        "attribution_class": str(fact.attribution_class),
        "attributed_orders": metrics.attributed_orders,
        "attributed_gmv_rub": gmv_token,
        "attributed_atc": metrics.attributed_atc,
        "attributed_units_shks": metrics.attributed_units_shks,
        "membership_snapshot_id": fact.provenance.membership_snapshot_id,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:32]


__all__ = ["semantic_observation_id"]
