"""Тексты Telegram-экранов рекламного контроля. Без записи и без экономики."""

from __future__ import annotations

from app.modules.ad_control_settings.ui.dry_run_preview import DryRunPreview
from app.modules.ad_control_settings.ui.view_models import (
    FeatureControlLine,
    ShopFeatureLine,
)

_BANNER = (
    "PREVIEW / DRY RUN только для действий кампании. "
    "Состояние в базе не меняется.\n"
    "Enrollment в Slice B не хранится: effective кампании fail-closed "
    "(NOT_ENROLLED), пока контроллер не записан отдельно.\n"
    "RUNTIME_ECONOMICS_NOT_AVAILABLE"
)


def format_shop_screen(
    *,
    shop_id: str,
    lines: tuple[ShopFeatureLine, ...],
) -> str:
    """Обзор shop configured features."""
    parts = [
        "Рекламный контроль",
        f"shop_id: {shop_id}",
        _BANNER,
        "",
        "Магазин (configured):",
    ]
    for line in lines:
        parts.append(
            f"• {line.feature_id.value} — {line.label}\n"
            f"  configured: {line.activation.value}\n"
            f"  payload: {line.payload_text}"
        )
    return "\n".join(parts)


def format_campaign_list(
    *,
    shop_id: str,
    page: int,
    pages: int,
    rows: tuple[tuple[int, str, str], ...],
) -> str:
    """Страница кампаний. Идентичность — advert_id. Третье поле — режимы."""
    parts = [
        "Рекламный контроль — кампании",
        f"shop_id: {shop_id}",
        f"страница {page}/{pages}",
        "Идентификатор: advert_id (не nmId).",
        "",
    ]
    if not rows:
        parts.append("Нет кампаний с advert_id.")
        return "\n".join(parts)
    for advert_id, name, modes in rows:
        label = name.strip() or "без названия"
        parts.append(f"adv {advert_id} — {label}\n  {modes}")
    return "\n".join(parts)


def format_campaign_detail(
    *,
    shop_id: str,
    advert_id: int,
    name: str,
    lines: tuple[FeatureControlLine, ...],
) -> str:
    """Карточка кампании: mode, configured, effective, provenance."""
    parts = [
        "Рекламный контроль — кампания",
        f"shop_id: {shop_id}",
        f"advert_id: {advert_id}",
        f"название (не ключ): {name.strip() or '—'}",
        _BANNER,
        "",
    ]
    for line in lines:
        parts.append(
            f"• {line.feature_id.value} — {line.label}\n"
            f"  mode: {line.campaign_mode.value}\n"
            f"  configured: {line.campaign_payload_text}\n"
            f"  shop: {line.shop_activation} {line.shop_payload_text}\n"
            f"  effective: {line.effective_text}\n"
            f"  provenance: {line.provenance_text}\n"
            f"  status: {line.status_text}"
        )
    return "\n".join(parts)


def format_feature_detail(line: FeatureControlLine, *, advert_id: int) -> str:
    """Одна feature перед dry-run."""
    return (
        f"Рекламный контроль — {line.label}\n"
        f"feature: {line.feature_id.value}\n"
        f"advert_id: {advert_id}\n"
        f"mode: {line.campaign_mode.value}\n"
        f"configured: {line.campaign_payload_text}\n"
        f"shop: {line.shop_activation} {line.shop_payload_text}\n"
        f"effective: {line.effective_text}\n"
        f"provenance: {line.provenance_text}\n"
        f"status: {line.status_text}\n"
        "\n"
        "Действия ниже — только просмотр dry-run."
    )


def format_dry_run(preview: DryRunPreview) -> str:
    """Человекочитаемый dry-run. Всегда помечен как preview."""
    revision = (
        "absent"
        if preview.expected_revision is None
        else str(preview.expected_revision)
    )
    parts = [
        "PREVIEW / DRY RUN",
        "Состояние в базе НЕ изменено. Apply не вызывался.",
        f"operation: {preview.operation}",
        f"expected_revision: {revision}",
        f"validation: {preview.validation_status}",
    ]
    if preview.validation_status == "no_op":
        parts.append("Изменений нет (NO_OP).")
    if preview.notes:
        parts.append("notes:")
        parts.extend(f"  {note}" for note in preview.notes)
    if preview.diff_lines:
        parts.append("diff:")
        parts.extend(f"  {line}" for line in preview.diff_lines)
    if preview.error_lines:
        parts.append("errors:")
        parts.extend(f"  {line}" for line in preview.error_lines)
    return "\n".join(parts)
