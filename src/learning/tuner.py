"""Tuner: propose a strategy config, evaluate it, keep it only if it beats the gate.

The tuner is the active half of the learning loop. Given past experiments it:

1. proposes the next config deterministically (coordinate ascent over field
   boosts -- no randomness);
2. evaluates the proposal by running the relevance evaluation over the checked-in
   judgments (reusing ``src.evaluation`` for the metric math -- never reimplemented);
3. keeps the proposal **only if** it passes the existing search-quality gate
   (``scripts.gate_search_quality.evaluate_gate``) *and* improves the headline
   metric versus the current best.

A kept proposal is recorded/staged in the experiment store. It is never promoted
to the live strategy config automatically -- promotion is an explicit, separate
step. When ``MEMORY_ENABLED`` is off (default), :func:`tune` is inert.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from scripts.gate_search_quality import evaluate_gate
from src.evaluation.relevance_report import (
    QueryJudgment,
    aggregate_by_strategy,
    evaluate_ranking,
)
from src.learning.config import StrategyConfig, baseline_config, build_query
from src.learning.experiments import ExperimentRecord, ExperimentStore

# A search function takes a fully-built Elasticsearch query body and returns the
# ranked product ids. Injecting it keeps the tuner offline-testable: tests pass a
# fake that returns canned rankings; the runner passes a live-ES-backed fn.
SearchFn = Callable[[dict[str, Any]], list[str]]

HEADLINE_METRIC = "precision_at_5"
# Multiplicative steps applied to one field boost at a time. Deterministic order.
BOOST_STEPS: tuple[float, ...] = (1.5, 0.5)
MIN_BOOST = 0.1
MAX_BOOST = 10.0


def memory_enabled() -> bool:
    """True only when MEMORY_ENABLED is explicitly truthy. Default: off."""

    return os.getenv("MEMORY_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def _round_boost(value: float) -> float:
    return round(max(MIN_BOOST, min(MAX_BOOST, value)), 4)


def propose_configs(
    base: StrategyConfig,
    tried: Iterable[StrategyConfig] = (),
) -> list[StrategyConfig]:
    """Deterministically enumerate candidate configs around ``base``.

    Coordinate ascent: for each field, scale its boost up then down by the fixed
    ``BOOST_STEPS``, holding the other boosts fixed. No randomness, stable order.
    Configs whose identity matches ``base`` or anything in ``tried`` are skipped.
    """

    seen = {base.key()} | {c.key() for c in tried}
    candidates: list[StrategyConfig] = []
    for field_name in sorted(base.field_boosts):
        for step in BOOST_STEPS:
            new_boosts = dict(base.field_boosts)
            new_boosts[field_name] = _round_boost(base.field_boosts[field_name] * step)
            candidate = base.with_boosts(new_boosts)
            if candidate.key() in seen:
                continue
            seen.add(candidate.key())
            candidates.append(candidate)
    return candidates


def evaluate_config(
    config: StrategyConfig,
    judgments: Sequence[QueryJudgment],
    search_fn: SearchFn,
    size: int = 10,
) -> dict[str, float]:
    """Run the config over the judgments and return the headline metrics.

    Reuses ``src.evaluation`` for all metric math (precision/recall/MRR/nDCG).
    """

    rows = []
    for judgment in judgments:
        body = build_query(config, judgment.query, size)
        ranked_ids = search_fn(body)
        rows.append(evaluate_ranking(config.strategy, judgment.query, judgment.judgments, ranked_ids))

    summary = aggregate_by_strategy(rows, baseline_strategy=config.strategy)
    row = next(r for r in summary if r["strategy"] == config.strategy)
    return {
        "precision_at_5": float(row["precision_at_5"]),
        "recall_at_5": float(row["recall_at_5"]),
        "mrr_at_10": float(row["mrr_at_10"]),
        "ndcg_at_10": float(row["ndcg_at_10"]),
    }


def _passes_gate(config: StrategyConfig, metrics: dict[str, float], gate_config: dict[str, Any]) -> bool:
    """Reuse the existing gate. p95 latency is satisfied with 0.0 (offline tuning)."""

    relevance_report = {"summary": [{"strategy": config.strategy, **metrics}]}
    latency_report = {"summary": [{"strategy": config.strategy, "p95": 0.0}]}
    gate = {**gate_config, "strategy": config.strategy}
    return evaluate_gate(gate, relevance_report, latency_report) == []


@dataclass(frozen=True)
class TuneDecision:
    """Outcome of one tuning run."""

    proposed: StrategyConfig | None
    kept: bool
    reason: str
    proposed_metrics: dict[str, float] | None = None
    baseline_metrics: dict[str, float] | None = None
    best_metrics: dict[str, float] | None = None
    record: ExperimentRecord | None = None

    def metric_delta(self, metric: str = HEADLINE_METRIC) -> float | None:
        if self.proposed_metrics is None or self.best_metrics is None:
            return None
        return self.proposed_metrics.get(metric, 0.0) - self.best_metrics.get(metric, 0.0)


def tune(
    *,
    strategy: str,
    judgments: Sequence[QueryJudgment],
    search_fn: SearchFn,
    store: ExperimentStore,
    gate_config: dict[str, Any],
    size: int = 10,
    headline_metric: str = HEADLINE_METRIC,
    persist_baseline: bool = True,
) -> TuneDecision:
    """Propose one config, evaluate it, and keep it only if it beats the gate.

    Returns a :class:`TuneDecision`. The proposal is persisted to ``store`` (with
    its ``gate_passed`` flag) regardless of whether it is kept, so the memory
    records rejected experiments too. A kept proposal is *staged*, never promoted
    to the live strategy config.

    Inert (returns ``kept=False``, ``reason="memory-disabled"``) when
    ``MEMORY_ENABLED`` is off.
    """

    if not memory_enabled():
        return TuneDecision(proposed=None, kept=False, reason="memory-disabled")

    base = baseline_config(strategy)

    # Establish the current best from memory; fall back to the baseline config's
    # own measured metrics so the very first run has something to beat.
    best_record = store.best(headline_metric)
    if best_record is not None:
        best_config = best_record.config
        best_metrics = best_record.metrics
    else:
        best_config = base
        best_metrics = evaluate_config(base, judgments, search_fn, size)
        if persist_baseline:
            store.append(
                ExperimentRecord.create(
                    config=base,
                    metrics=best_metrics,
                    gate_passed=_passes_gate(base, best_metrics, gate_config),
                    note="baseline",
                )
            )

    tried = [r.config for r in store.all()]
    candidates = propose_configs(best_config, tried=tried)
    if not candidates:
        return TuneDecision(
            proposed=None,
            kept=False,
            reason="no-new-candidates",
            best_metrics=best_metrics,
        )

    proposed = candidates[0]
    metrics = evaluate_config(proposed, judgments, search_fn, size)
    gate_passed = _passes_gate(proposed, metrics, gate_config)
    improves = metrics.get(headline_metric, 0.0) > best_metrics.get(headline_metric, 0.0)
    kept = gate_passed and improves

    if not gate_passed:
        reason = "rejected: below gate"
    elif not improves:
        reason = f"rejected: does not improve {headline_metric}"
    else:
        reason = f"kept: passes gate and improves {headline_metric}"

    record = ExperimentRecord.create(
        config=proposed,
        metrics=metrics,
        gate_passed=gate_passed,
        note=f"staged ({reason})" if kept else reason,
        extra={"kept": kept, "baseline_strategy": strategy},
    )
    store.append(record)

    return TuneDecision(
        proposed=proposed,
        kept=kept,
        reason=reason,
        proposed_metrics=metrics,
        baseline_metrics=best_metrics if best_record is None else None,
        best_metrics=best_metrics,
        record=record,
    )
