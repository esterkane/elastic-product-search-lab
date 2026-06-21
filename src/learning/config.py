"""Tunable strategy configuration for the learning loop.

The *config* the tuner proposes is the set of per-field boosts of a strategy's
``multi_match`` query. These mirror the field boosts used by the live strategies
in ``scripts/evaluate_relevance.py`` (``boosted_bm25``, ``enriched_profile``) and
``src/search/hybrid_search.py`` (``baseline_bm25``), but live in their own,
immutable baseline so the tuner can explore copies without touching the live
strategy code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

# Baseline field boosts, copied verbatim from the live strategy query builders so
# that a "no-op" learning run reproduces the current strategy ranking. Keeping
# these as a separate source of truth is deliberate: the tuner mutates copies of
# these dictionaries and never the live builders.
BASELINE_FIELD_BOOSTS: dict[str, dict[str, float]] = {
    "baseline_bm25": {
        "title": 4.0,
        "brand": 2.0,
        "category": 1.5,
        "description": 0.8,
        "catalog_text": 0.5,
    },
    "boosted_bm25": {
        "title": 4.0,
        "brand": 2.0,
        "category": 1.5,
        "description": 1.0,
        "catalog_text": 0.8,
    },
    "enriched_profile": {
        "search_profile": 3.0,
        "title": 2.0,
        "category": 1.5,
        "brand": 1.0,
        "description": 0.5,
    },
}

# Per-strategy match options that are *not* tuned but are needed to build a
# faithful query body. Kept beside the boosts so ``build_query`` is self-contained.
_MATCH_OPTIONS: dict[str, dict[str, Any]] = {
    "baseline_bm25": {"type": "best_fields", "operator": "and"},
    "boosted_bm25": {
        "type": "best_fields",
        "operator": "or",
        "minimum_should_match": "2<75%",
        "fuzziness": "AUTO",
    },
    "enriched_profile": {
        "type": "best_fields",
        "operator": "or",
        "minimum_should_match": "2<70%",
        "fuzziness": "AUTO",
    },
}


@dataclass(frozen=True)
class StrategyConfig:
    """A tunable strategy configuration: a strategy name plus its field boosts."""

    strategy: str
    field_boosts: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "field_boosts": dict(sorted(self.field_boosts.items())),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StrategyConfig":
        return cls(
            strategy=str(data["strategy"]),
            field_boosts={str(k): float(v) for k, v in dict(data.get("field_boosts", {})).items()},
        )

    def with_boosts(self, field_boosts: Mapping[str, float]) -> "StrategyConfig":
        return StrategyConfig(strategy=self.strategy, field_boosts={str(k): float(v) for k, v in field_boosts.items()})

    def key(self) -> tuple[str, tuple[tuple[str, float], ...]]:
        """A hashable identity used to dedupe already-tried configs."""

        return (self.strategy, tuple(sorted((k, round(v, 4)) for k, v in self.field_boosts.items())))


BASELINE_STRATEGY_CONFIGS: dict[str, StrategyConfig] = {
    strategy: StrategyConfig(strategy=strategy, field_boosts=dict(boosts))
    for strategy, boosts in BASELINE_FIELD_BOOSTS.items()
}


def baseline_config(strategy: str) -> StrategyConfig:
    """Return the immutable baseline config for ``strategy``."""

    if strategy not in BASELINE_STRATEGY_CONFIGS:
        raise ValueError(f"Unknown tunable strategy: {strategy!r}. Known: {sorted(BASELINE_STRATEGY_CONFIGS)}")
    base = BASELINE_STRATEGY_CONFIGS[strategy]
    return StrategyConfig(strategy=base.strategy, field_boosts=dict(base.field_boosts))


def _format_fields(field_boosts: Mapping[str, float]) -> list[str]:
    # Stable field order keeps generated query bodies deterministic.
    formatted: list[str] = []
    for name in sorted(field_boosts):
        boost = field_boosts[name]
        # Render integer-valued boosts without a trailing ".0" to match hand-written queries.
        boost_str = str(int(boost)) if float(boost).is_integer() else f"{boost:g}"
        formatted.append(f"{name}^{boost_str}")
    return formatted


def build_query(config: StrategyConfig, query: str, size: int) -> dict[str, Any]:
    """Build an Elasticsearch query body for a tunable strategy config.

    Mirrors the live ``multi_match`` strategies but reads its field boosts from
    ``config`` so the tuner can vary them. The ``function_score`` wrappers used by
    ``boosted_bm25`` are intentionally omitted here because their factors are not
    part of the tuned surface; the boosts are what the tuner explores.
    """

    if config.strategy not in _MATCH_OPTIONS:
        raise ValueError(f"Unknown tunable strategy: {config.strategy!r}")
    if not config.field_boosts:
        raise ValueError("StrategyConfig.field_boosts must not be empty")

    options = dict(_MATCH_OPTIONS[config.strategy])
    multi_match: dict[str, Any] = {"query": query, "fields": _format_fields(config.field_boosts), **options}
    return {"size": size, "query": {"multi_match": multi_match}, "sort": ["_score"]}
