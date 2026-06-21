"""Tests for the procedural-learning loop: experiment store + tuner.

All offline (no live Elasticsearch). They prove:
- a proposed config that worsens the gate is rejected (never kept);
- a proposed config that beats the gate and improves the headline metric is kept;
- the experiment store round-trips a record (config + metrics + gate_passed);
- MEMORY_ENABLED off (default) makes the tuner inert.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from src.evaluation.relevance_report import QueryJudgment
from src.learning.config import StrategyConfig, baseline_config, build_query
from src.learning.experiments import (
    ExperimentRecord,
    FileExperimentStore,
    InMemoryExperimentStore,
)
from src.learning.tuner import propose_configs, tune

# A single judged query is enough to drive Precision@5 / MRR@10 deterministically.
JUDGMENTS = [
    QueryJudgment(
        query="wireless headphones",
        judgments={"P1": 3, "P2": 2, "P3": 0, "P4": 0},
    )
]

# Gate the proposal must beat. Matches the shape of config/relevance-gate.json.
GATE_CONFIG = {
    "thresholds": {
        "minimum_average_precision_at_5": 0.5,
        "minimum_average_mrr_at_10": 0.5,
        "maximum_p95_latency_ms": 500,
    }
}


def _proposed_config() -> StrategyConfig:
    """The exact config the tuner will propose first for enriched_profile."""

    base = baseline_config("enriched_profile")
    return propose_configs(base)[0]


def _boosts_key(config: StrategyConfig) -> Any:
    return config.key()


def _make_search_fn(rankings_by_config: dict[Any, list[str]], default: list[str]):
    """Return a fake search fn that maps the query body's boosts to canned rankings.

    The body encodes the field boosts via its multi_match ``fields`` list, so the
    fn can return a different ranking for the baseline vs the proposed config.
    """

    def search_fn(body: dict[str, Any]) -> list[str]:
        fields = tuple(body["query"]["multi_match"]["fields"])
        return rankings_by_config.get(fields, default)

    return search_fn


def _fields_tuple_for(config: StrategyConfig, query: str) -> tuple[str, ...]:
    body = build_query(config, query, 10)
    return tuple(body["query"]["multi_match"]["fields"])


def _fields_tuple(config: StrategyConfig) -> tuple[str, ...]:
    return _fields_tuple_for(config, "wireless headphones")


def _enable_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEMORY_ENABLED", "true")


# --------------------------------------------------------------------------- #
# Experiment store round-trip
# --------------------------------------------------------------------------- #
def test_experiment_store_round_trips_record(tmp_path: Path):
    store = FileExperimentStore(tmp_path / "experiments.jsonl")
    config = StrategyConfig(strategy="enriched_profile", field_boosts={"title": 2.0, "brand": 1.0})
    record = ExperimentRecord.create(
        config=config,
        metrics={"precision_at_5": 0.6, "mrr_at_10": 0.7, "ndcg_at_10": 0.65},
        gate_passed=True,
        note="unit",
    )

    store.append(record)
    reloaded = store.all()

    assert len(reloaded) == 1
    got = reloaded[0]
    assert got.config.strategy == "enriched_profile"
    assert got.config.field_boosts == {"title": 2.0, "brand": 1.0}
    assert got.metrics == {"precision_at_5": 0.6, "mrr_at_10": 0.7, "ndcg_at_10": 0.65}
    assert got.gate_passed is True
    assert got.note == "unit"


def test_experiment_store_best_picks_highest_gate_passing(tmp_path: Path):
    store = FileExperimentStore(tmp_path / "experiments.jsonl")
    low = ExperimentRecord.create(baseline_config("enriched_profile"), {"precision_at_5": 0.4}, gate_passed=True)
    high = ExperimentRecord.create(
        baseline_config("enriched_profile").with_boosts({"title": 9.0}),
        {"precision_at_5": 0.9},
        gate_passed=True,
    )
    failing = ExperimentRecord.create(
        baseline_config("enriched_profile").with_boosts({"title": 1.0}),
        {"precision_at_5": 0.99},
        gate_passed=False,
    )
    store.append(low)
    store.append(high)
    store.append(failing)

    best = store.best("precision_at_5")
    assert best is not None
    assert best.metrics["precision_at_5"] == 0.9  # failing one ignored despite higher score


# --------------------------------------------------------------------------- #
# MEMORY_ENABLED gating
# --------------------------------------------------------------------------- #
def test_tuner_is_inert_when_memory_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("MEMORY_ENABLED", raising=False)
    store = InMemoryExperimentStore()

    decision = tune(
        strategy="enriched_profile",
        judgments=JUDGMENTS,
        search_fn=_make_search_fn({}, default=["P1", "P2"]),
        store=store,
        gate_config=GATE_CONFIG,
    )

    assert decision.kept is False
    assert decision.reason == "memory-disabled"
    assert decision.proposed is None
    assert store.all() == []  # nothing persisted


# --------------------------------------------------------------------------- #
# Reject-on-worse (the key test) and keep-on-better
# --------------------------------------------------------------------------- #
def test_proposal_that_worsens_gate_is_rejected(monkeypatch: pytest.MonkeyPatch):
    _enable_memory(monkeypatch)
    store = InMemoryExperimentStore()

    base = baseline_config("enriched_profile")
    proposed = _proposed_config()

    # Baseline ranks the relevant docs first (Precision@5 = 0.5, MRR = 1.0 -> passes
    # the gate, sets the bar). The proposed config surfaces only non-relevant docs,
    # so Precision@5 = 0 and MRR@10 = 0: below the gate. The tuner must NOT keep it.
    rankings = {
        _fields_tuple(base): ["P1", "P2", "P3", "P4"],   # passes the gate
        _fields_tuple(proposed): ["P3", "P4"],           # fails the gate
    }

    decision = tune(
        strategy="enriched_profile",
        judgments=JUDGMENTS,
        search_fn=_make_search_fn(rankings, default=[]),
        store=store,
        gate_config=GATE_CONFIG,
    )

    assert decision.proposed == proposed
    assert decision.kept is False
    assert "below gate" in decision.reason
    # The rejected experiment is still recorded (memory keeps failures), flagged not-kept.
    persisted = store.all()
    assert any(r.config.key() == proposed.key() and r.gate_passed is False for r in persisted)
    assert all(r.extra.get("kept", False) is False for r in persisted)


def test_proposal_that_beats_gate_is_kept(monkeypatch: pytest.MonkeyPatch):
    _enable_memory(monkeypatch)
    store = InMemoryExperimentStore()

    base = baseline_config("enriched_profile")
    proposed = _proposed_config()

    # One judged query with two relevant docs. The baseline surfaces only one
    # relevant doc in its top results (Precision@5 = 0.5 -> passes the gate, sets
    # the bar). The proposed config surfaces both (Precision@5 = 1.0): it beats
    # the gate AND improves the headline metric, so it must be kept (staged).
    judgments = [QueryJudgment(query="q", judgments={"P1": 3, "P2": 2, "P3": 0})]
    rankings = {
        _fields_tuple_for(base, "q"): ["P1", "P3"],      # P@5 = 0.5 -> passes, current best
        _fields_tuple_for(proposed, "q"): ["P1", "P2"],  # P@5 = 1.0 -> beats gate + improves
    }

    decision = tune(
        strategy="enriched_profile",
        judgments=judgments,
        search_fn=_make_search_fn(rankings, default=[]),
        store=store,
        gate_config=GATE_CONFIG,
    )

    assert decision.proposed == proposed
    assert decision.kept is True
    assert "kept" in decision.reason
    assert decision.proposed_metrics is not None
    assert decision.proposed_metrics["precision_at_5"] == 1.0
    assert decision.metric_delta("precision_at_5") == pytest.approx(0.5)
    # Kept proposal is staged in memory, flagged kept=True; live config untouched.
    kept_records = [r for r in store.all() if r.extra.get("kept") is True]
    assert len(kept_records) == 1
    assert kept_records[0].config.key() == proposed.key()


def test_propose_configs_is_deterministic_and_skips_tried():
    base = baseline_config("enriched_profile")
    first = propose_configs(base)
    second = propose_configs(base)
    assert [c.key() for c in first] == [c.key() for c in second]  # deterministic

    # Passing the first candidate as already-tried removes it from the next proposal set.
    skip = propose_configs(base, tried=[first[0]])
    assert first[0].key() not in {c.key() for c in skip}


def test_build_query_reflects_tuned_boosts():
    config = StrategyConfig(strategy="enriched_profile", field_boosts={"title": 5.0, "brand": 2.0})
    body = build_query(config, "shoes", 7)
    assert body["size"] == 7
    assert body["query"]["multi_match"]["fields"] == ["brand^2", "title^5"]
    assert body["query"]["multi_match"]["query"] == "shoes"
