"""Shared logic for effective keyword target place with individual_keywords_target_place_mode."""

from typing import Literal

TargetPlaceSource = Literal["individual", "campaign", "default"]

DEFAULT_SOURCE_LABELS: dict[TargetPlaceSource, str] = {
    "individual": "индивидуальная",
    "campaign": "по кампании",
    "default": "по умолчанию",
}


def get_effective_keyword_target_place(
    keyword_or_setting: object,
    adv_setting: object,
) -> tuple[int | None, TargetPlaceSource]:
    """
    Effective target place for a keyword and its source.

    - If individual_keywords_target_place_mode is on and keyword has target_place > 0:
      return (target_place, "individual").
    - Else if campaign has max_place > 0: return (max_place, "campaign").
    - Else: return (None, "default").
    """
    use_individual = bool(getattr(adv_setting, "individual_keywords_target_place_mode", False))
    kw_place = getattr(keyword_or_setting, "target_place", None)
    if use_individual and isinstance(kw_place, int) and kw_place > 0:
        return (kw_place, "individual")
    camp_place = getattr(adv_setting, "max_place", None)
    if isinstance(camp_place, int) and camp_place > 0:
        return (camp_place, "campaign")
    return (None, "default")


def format_target_place_display(
    value: int | None,
    source: TargetPlaceSource,
    labels: dict[TargetPlaceSource, str] | None = None,
) -> tuple[str, str]:
    """Return (value_str, source_label). Uses DEFAULT_SOURCE_LABELS if labels is None."""
    value_str = str(value) if value is not None else "Не задана"
    lab = labels if labels is not None else DEFAULT_SOURCE_LABELS
    source_label = lab.get(source, DEFAULT_SOURCE_LABELS[source])
    return (value_str, source_label)
