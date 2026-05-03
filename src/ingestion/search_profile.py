"""Deterministic product search-profile enrichment."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _attribute_values(attributes: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in sorted(attributes):
        value = _stringify(attributes[key])
        if value and key != "product_locale":
            values.append(value)
    return values


def _inferred_use_cases(title: str, category: str, description: str, attributes: Mapping[str, Any]) -> list[str]:
    text = " ".join([title, category, description, " ".join(_attribute_values(attributes))]).lower()
    use_cases: list[str] = []
    rules = [
        (("headphone", "noise cancel", "bluetooth"), ["travel", "office", "commuting", "music"]),
        (("mouse", "keyboard", "computer accessories"), ["work", "gaming", "home office"]),
        (("backpack", "laptop", "waterproof"), ["commuting", "school", "travel", "laptop carry"]),
        (("coffee", "espresso", "maker"), ["coffee", "kitchen", "morning routine", "coffee machine"]),
        (("charger", "power bank", "usb-c", "usb c"), ["laptop charging", "travel", "mobile devices"]),
        (("water bottle", "travel mug", "insulated"), ["hydration", "gym", "commuting", "outdoors"]),
        (("cast iron", "skillet", "cookware"), ["camping", "stovetop", "oven cooking"]),
        (("smartwatch", "running", "fitness"), ["running", "training", "fitness"]),
        (("ebook", "e-reader", "reader", "waterproof"), ["reading", "travel", "beach", "commuting"]),
        (("speaker", "ssd", "airtag", "tracker"), ["gift", "gamer", "tech gift"]),
        (("skin care", "serum", "ordinary"), ["self care", "beauty", "skin routine"]),
    ]
    for triggers, additions in rules:
        if any(trigger in text for trigger in triggers):
            for addition in additions:
                if addition not in use_cases:
                    use_cases.append(addition)
    explicit = _stringify(attributes.get("target_audience") or attributes.get("audience") or attributes.get("use_case"))
    if explicit:
        for item in explicit.split(","):
            cleaned = item.strip()
            if cleaned and cleaned not in use_cases:
                use_cases.append(cleaned)
    return use_cases


def build_search_profile(product: Mapping[str, Any]) -> str:
    """Build deterministic plain text used for enriched product retrieval."""

    title = _stringify(product.get("title") or product.get("name"))
    brand = _stringify(product.get("brand"))
    category = _stringify(product.get("category"))
    description = _stringify(product.get("description"))
    raw_attributes = product.get("attributes") or {}
    attributes: Mapping[str, Any] = raw_attributes if isinstance(raw_attributes, Mapping) else {}

    color = _stringify(attributes.get("color") or product.get("color"))
    material = _stringify(attributes.get("material") or product.get("material"))
    tags = _stringify(attributes.get("tags") or product.get("tags"))
    use_cases = _inferred_use_cases(title, category, description, attributes)
    attribute_values = _attribute_values(attributes)

    parts = []
    if title:
        parts.append(f"Product: {title}.")
    if brand:
        parts.append(f"Brand: {brand}.")
    if category:
        parts.append(f"Category: {category}.")
    if description:
        parts.append(f"Description: {description}.")
    if color:
        parts.append(f"Color: {color}.")
    if material:
        parts.append(f"Material: {material}.")
    if use_cases:
        parts.append(f"Useful for: {', '.join(use_cases)}.")
    if tags:
        parts.append(f"Tags: {tags}.")
    if attribute_values:
        parts.append(f"Attributes: {', '.join(attribute_values)}.")

    return " ".join(parts)
