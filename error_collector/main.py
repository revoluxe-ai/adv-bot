"""Error collector service for Fluent Bit webhook ingestion and Telegram digests."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from error_collector.redis_client import get_redis_client

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))

MSK = timezone(timedelta(hours=3))
DEFAULT_MAX_MESSAGE_LENGTH = 4000
DEFAULT_TOP_N_ERRORS = 10
DEFAULT_TTL_HOURS = 24 * 31
DEFAULT_DIGEST_LOOKBACK_HOURS = 1

app = FastAPI(title="error-collector", version="1.0.0")


class DigestResponse(BaseModel):
    sent: bool
    message: str
    errors_count: int = 0


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for %s=%r, fallback=%s", name, raw, default)
        return default


def _extract_metadata(record: dict[str, Any]) -> tuple[str, str, str]:
    kube_obj = record.get("kubernetes")
    kube = cast(dict[str, Any] | None, kube_obj if isinstance(kube_obj, dict) else None)
    if isinstance(kube, dict):
        ns = str(kube.get("namespace_name", "unknown") or "unknown")
        pod = str(kube.get("pod_name", "unknown") or "unknown")
        container = str(kube.get("container_name", "unknown") or "unknown")
        return ns, pod, container
    ns = str(record.get("kubernetes_namespace_name") or "unknown")
    pod = str(record.get("kubernetes_pod_name") or "unknown")
    container = str(record.get("kubernetes_container_name") or "unknown")
    return ns, pod, container


def _extract_log_text(record: dict[str, Any]) -> str:
    candidate = record.get("log")
    if isinstance(candidate, str) and candidate.strip():
        return candidate.strip()
    if isinstance(candidate, (dict, list)):
        return json.dumps(candidate, ensure_ascii=False)[:2000]
    return str(candidate or "").strip()


def _normalize_signature(log_text: str) -> str:
    first_line = log_text.splitlines()[0] if log_text else "EMPTY_LOG"
    cleaned = first_line.strip()
    if not cleaned:
        return "EMPTY_LOG"
    return cleaned[:500]


async def _store_error(record: dict[str, Any]) -> None:
    redis_host = os.getenv("REDIS_HOST", "")
    if not redis_host:
        raise RuntimeError("REDIS_HOST is required")
    redis_port = _env_int("REDIS_PORT", 6379)
    redis_password = os.getenv("REDIS_PASSWORD") or None
    redis = await get_redis_client(
        host=redis_host,
        port=redis_port,
        password=redis_password,
    )

    now = datetime.now(timezone.utc)
    bucket_hour = now.strftime("%Y%m%d%H")
    ttl_hours = _env_int("ERROR_TTL_HOURS", DEFAULT_TTL_HOURS)
    ttl_seconds = max(3600, ttl_hours * 3600)

    log_text = _extract_log_text(record)
    signature = _normalize_signature(log_text)
    signature_hash = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:16]
    key = f"errors:bucket:{bucket_hour}:{signature_hash}"

    namespace, pod, container = _extract_metadata(record)
    sample = log_text[:1500]

    now_iso = now.isoformat()
    first_ts = await redis.hget(key, "first_ts")
    if first_ts is None:
        _ = await redis.hset(key, "first_ts", now_iso)
    _ = await redis.hset(key, "last_ts", now_iso)
    _ = await redis.hset(key, "signature", signature)
    _ = await redis.hset(key, "namespace", namespace)
    _ = await redis.hset(key, "pod", pod)
    _ = await redis.hset(key, "container", container)
    _ = await redis.hset(key, "sample", sample)
    _ = await redis.hincrby(key, "count", 1)
    _ = await redis.expire(key, ttl_seconds)


async def _send_telegram_message(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            raise RuntimeError(f"Telegram API error {resp.status_code}: {resp.text[:300]}")


async def _build_digest_lines(hour_bucket: str) -> list[str]:
    redis_host = os.getenv("REDIS_HOST", "")
    if not redis_host:
        raise RuntimeError("REDIS_HOST is required")
    redis_port = _env_int("REDIS_PORT", 6379)
    redis_password = os.getenv("REDIS_PASSWORD") or None
    redis = await get_redis_client(
        host=redis_host,
        port=redis_port,
        password=redis_password,
    )
    keys = await redis.keys(f"errors:bucket:{hour_bucket}:*")
    if not keys:
        return []

    items: list[tuple[int, dict[str, str]]] = []
    for key in keys:
        raw_data = await redis.hgetall(key)
        data = {str(k): str(v) for k, v in raw_data.items()}
        count = int(data.get("count", "0"))
        if count <= 0:
            continue
        items.append((count, data))

    items.sort(key=lambda x: x[0], reverse=True)
    top_n = _env_int("TOP_N_ERRORS", DEFAULT_TOP_N_ERRORS)
    top = items[: max(1, top_n)]
    lines: list[str] = []
    for idx, (count, data) in enumerate(top, start=1):
        signature = data.get("signature", "unknown")
        namespace = data.get("namespace", "unknown")
        pod = data.get("pod", "unknown")
        lines.append(
            f"{idx}. x{count} [{namespace}] {pod}\n{signature}"
        )
    return lines


@app.get("/health")
async def health() -> dict[str, str]:
    redis_host = os.getenv("REDIS_HOST", "")
    if not redis_host:
        raise HTTPException(status_code=500, detail="REDIS_HOST is required")
    redis_port = _env_int("REDIS_PORT", 6379)
    redis_password = os.getenv("REDIS_PASSWORD") or None
    redis = await get_redis_client(
        host=redis_host,
        port=redis_port,
        password=redis_password,
    )
    _ = await redis.ping()
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    accepted = 0
    if isinstance(payload, dict):
        await _store_error(cast(dict[str, Any], payload))
        accepted = 1
    elif isinstance(payload, list):
        records = cast(list[Any], payload)
        for item in records:
            if isinstance(item, dict):
                await _store_error(cast(dict[str, Any], item))
                accepted += 1
    else:
        raise HTTPException(status_code=400, detail="JSON object or array expected")
    if accepted == 0:
        raise HTTPException(status_code=400, detail="No valid records in payload")
    return {"status": "accepted", "accepted_records": accepted}


@app.post("/send-digest", response_model=DigestResponse)
async def send_digest() -> DigestResponse:
    lookback = max(1, _env_int("DIGEST_LOOKBACK_HOURS", DEFAULT_DIGEST_LOOKBACK_HOURS))
    msk_now = datetime.now(MSK).replace(minute=0, second=0, microsecond=0)
    target_hour = msk_now - timedelta(hours=lookback)
    hour_bucket = target_hour.astimezone(timezone.utc).strftime("%Y%m%d%H")

    lines = await _build_digest_lines(hour_bucket)
    if not lines:
        return DigestResponse(
            sent=False,
            message=f"No errors for bucket {hour_bucket}",
            errors_count=0,
        )

    max_len = _env_int("MAX_MESSAGE_LENGTH", DEFAULT_MAX_MESSAGE_LENGTH)
    header = f"Ошибка-дайджест за {target_hour.strftime('%Y-%m-%d %H:00')} (MSK)\n"
    body = "\n\n".join(lines)
    text = (header + body).strip()
    if len(text) > max_len:
        text = text[: max_len - 30] + "\n\n... truncated ..."

    await _send_telegram_message(text)
    return DigestResponse(sent=True, message="Digest sent", errors_count=len(lines))
