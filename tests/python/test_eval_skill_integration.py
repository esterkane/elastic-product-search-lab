"""Offline unit tests for the shared ``relevance_eval`` skill integration.

No live Elasticsearch and no network: the search function is faked (canned
rankings) and the adapter is exercised by monkeypatching ``search_products`` to
return canned hits. These cover (a) that the committed judgments + thresholds
files drive the skill's harness/gate to a known pass and a known fail, and
(b) that the thin adapter extracts product ids in ranked order.

These tests require the ``eval`` optional dependency (the ``relevance_eval``
skill). They are plain unit tests — they run under ``pytest -m "not integration"``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

relevance_eval = pytest.importorskip(
    "relevance_eval",
    reason="install the eval extra: pip install -e '.[eval]'",
)
run_evaluation = relevance_eval.run_evaluation
evaluate_thresholds = relevance_eval.evaluate_thresholds
load_thresholds = relevance_eval.load_thresholds

from scripts.eval_with_skill import load_judgments_as_map  # noqa: E402
from src.eval.skill_adapter import make_search_fn  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
JUDGMENTS_PATH = PROJECT_ROOT / "data" / "judgments" / "product_search_judgments.json"
THRESHOLDS_PATH = PROJECT_ROOT / "config" / "eval_thresholds.json"
STRATEGIES = ("baseline_bm25", "boosted_bm25", "enriched_profile")


def _perfect_search_fn(judgments):
    """A fake search_fn that returns every judged id, graded-best first."""

    def search(query: str, strategy: str) -> list[str]:
        graded = judgments[query]
        return sorted(graded, key=lambda doc_id: graded[doc_id], reverse=True)

    return search


def test_committed_files_load_in_skill_shapes() -> None:
    judgments = load_judgments_as_map(JUDGMENTS_PATH)
    thresholds = load_thresholds(str(THRESHOLDS_PATH))

    # Judgments: flat {query: {id: grade}} the skill expects.
    assert judgments["wireless noise cancelling headphones"]["P100002"] == 3
    assert all(isinstance(grades, dict) for grades in judgments.values())

    # Thresholds: "<metric>@<k>" keys per strategy.
    assert thresholds["enriched_profile"]["precision@5"] == pytest.approx(0.6)
    assert thresholds["enriched_profile"]["mrr@10"] == pytest.approx(0.75)


def test_run_evaluation_report_shape_over_committed_judgments() -> None:
    judgments = load_judgments_as_map(JUDGMENTS_PATH)
    report = run_evaluation(
        judgments, _perfect_search_fn(judgments), list(STRATEGIES), ks=(1, 5, 10)
    )

    assert report["queries"] == len(judgments)
    assert set(report["strategies"]) == set(STRATEGIES)
    metrics = report["strategies"]["enriched_profile"]["metrics"]
    assert set(metrics) >= {"precision", "mrr", "ndcg"}
    # Every judged query has at least one relevant id, so MRR@10 is a perfect 1.0.
    assert metrics["mrr"]["10"] == pytest.approx(1.0)


def test_gate_passes_when_rankings_are_perfect() -> None:
    # A ranking that puts the most-relevant judged id first means MRR@10 == 1.0
    # for every query, so an MRR-based gate passes. (Precision@5's denominator is
    # k=5, and the judged sets have only 2-3 relevant ids each, so precision@5 is
    # intentionally not asserted here — that gate is meaningful against a live
    # index, exercised by scripts/eval_with_skill.py.)
    judgments = load_judgments_as_map(JUDGMENTS_PATH)
    report = run_evaluation(
        judgments, _perfect_search_fn(judgments), list(STRATEGIES), ks=(1, 3, 5, 10)
    )
    gate = evaluate_thresholds(report, {"default": {"mrr@10": 0.75}})
    assert gate["passed"] is True
    assert gate["checks"], "expected at least one threshold check"


def test_committed_thresholds_gate_against_perfect_rankings() -> None:
    # The committed config/eval_thresholds.json mirrors the repo's existing
    # relevance gate (precision@5 >= 0.6). With only 2-3 relevant ids per query
    # the tiny fake search cannot satisfy precision@5, so the committed gate is a
    # known FAIL here — proving the threshold keys are read and enforced.
    judgments = load_judgments_as_map(JUDGMENTS_PATH)
    thresholds = load_thresholds(str(THRESHOLDS_PATH))
    report = run_evaluation(
        judgments, _perfect_search_fn(judgments), list(STRATEGIES), ks=(1, 3, 5, 10)
    )
    gate = evaluate_thresholds(report, thresholds)
    assert gate["passed"] is False
    failing = {c["metric"] for c in gate["checks"] if not c["passed"]}
    assert "precision@5" in failing


def test_gate_fails_when_search_returns_nothing() -> None:
    judgments = load_judgments_as_map(JUDGMENTS_PATH)
    thresholds = load_thresholds(str(THRESHOLDS_PATH))

    def empty_search(query: str, strategy: str) -> list[str]:
        return []

    report = run_evaluation(judgments, empty_search, list(STRATEGIES), ks=(1, 3, 5, 10))
    gate = evaluate_thresholds(report, thresholds)
    assert gate["passed"] is False


def test_adapter_extracts_product_ids_in_ranked_order(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_search_products(client, index_name, query, strategy, size):
        captured["client"] = client
        captured["index_name"] = index_name
        captured["query"] = query
        captured["strategy"] = strategy
        captured["size"] = size
        return {
            "strategy": strategy,
            "query": query,
            "products": [
                {"productId": "P100002"},
                {"productId": "P100022"},
                {"productId": "P100013"},
            ],
        }

    # Patch the name the adapter actually calls.
    monkeypatch.setattr("src.eval.skill_adapter.search_products", fake_search_products)

    sentinel_client = object()
    search = make_search_fn(sentinel_client, index_name="products-v1", size=7)
    ids = search("wireless headphones", "enriched_profile")

    assert ids == ["P100002", "P100022", "P100013"]
    assert captured["client"] is sentinel_client
    assert captured["index_name"] == "products-v1"
    assert captured["strategy"] == "enriched_profile"
    assert captured["size"] == 7


def test_adapter_accepts_a_client_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    made: dict[str, object] = {}

    def fake_search_products(client, index_name, query, strategy, size):
        made["client"] = client
        return {"products": [{"productId": "P1"}]}

    monkeypatch.setattr("src.eval.skill_adapter.search_products", fake_search_products)

    real_client = object()
    factory_calls = {"n": 0}

    def factory():
        factory_calls["n"] += 1
        return real_client

    search = make_search_fn(factory)
    assert search("q", "baseline_bm25") == ["P1"]
    # Resolved lazily and only once.
    search("q2", "baseline_bm25")
    assert factory_calls["n"] == 1
    assert made["client"] is real_client


def test_judgments_file_is_well_formed_json() -> None:
    rows = json.loads(JUDGMENTS_PATH.read_text(encoding="utf-8"))
    assert isinstance(rows, list) and rows
    assert all("query" in row and "judgments" in row for row in rows)
